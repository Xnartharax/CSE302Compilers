from dataclasses import field
from .bxast import *
from typing import Dict, Set

class TACTemp:
    def __init__(self, id: str | int) -> None:
        self.id = id

    def __str__(self):
        return f"%{self.id}"

    def __repr__(self):
        return f"%{self.id}"

    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class TACGlobal:
    name: str

    def __str__(self) -> str:
        return f"@{self.name}"

    def __eq__(self, __value: object) -> bool:
        return self.name == __value.name


@dataclass
class TACGlobalDecl:
    glob: TACGlobal
    init: int

    def __str__(self) -> str:
        return f"{self.glob} = {self.init}"


@dataclass
class TACLabel:
    name: str

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __value: object) -> bool:
        return __value.name == self.name

    def __str__(self):
        return f"%{self.name}"


@dataclass
class TACOp:
    opcode: str
    args: List[TACTemp | TACLabel | int | TACGlobal]
    result: TACTemp | TACGlobal | None

    # for liveness analysis
    live_in: Set[TACTemp] = field(default_factory=set)
    live_out: Set[TACTemp] = field(default_factory=set)

    def to_dict(self):
        return {
            "opcode": self.opcode,
            "args": [
                str(arg) if isinstance(arg, TACTemp) else arg for arg in self.args
            ],
            "result": str(self.result)
            if isinstance(self.result, TACTemp)
            else self.result,
        }

    def pretty(self):
        if self.result is not None:
            return (
                f"{self.result} = {self.opcode} {' '.join([str(arg) for arg in self.args])}"
            )
        return (
               f"{self.opcode} {' '.join([str(arg) for arg in self.args])}"
            )

    def detailed(self) -> str:
        return f"\t{str(self.live_in)} \n\t{self.pretty()}\n \t{str(self.live_out)}"

@dataclass
class TAC:
    ops: List[TACOp | TACLabel]

    def get_tmps(self):
        temps = set()
        for op in self.ops:
            if isinstance(op, TACOp):
                if (
                    op.result is not None
                ):  # only results can that are written to can be tacops
                    temps.add(op.result)
        return temps


@dataclass
class TACProc:
    name: str
    body: TAC
    params: List[TACTemp]


OPCODES = [
    "jmp",
    "jz",
    "jnz",
    "jl",
    "jle",
    "jnl",
    "jnle",
    "ret",
    "lshift",
    "rshift",
    "mod",
    "div",
    "add",
    "sub",
    "mul",
    "and",
    "or",
    "xor",
    "not",
    "neg",
    "print",
    "copy",
    "const",
    "param",
    "call",
]

JMP_OPS = ["jmp", "jz", "jnz", "jl", "jle", "jnl", "jnle", "ret"]

UNCOND_JMP_OP = ["jmp", "ret"]
COND_JMP_OPS = [op for op in JMP_OPS if op not in UNCOND_JMP_OP]

SIMPLE_OPS = [opcode for opcode in OPCODES if opcode not in JMP_OPS]
OPERATOR_TO_OPCODE = {
    "addition": "add",
    "subtraction": "sub",
    "multiplication": "mul",
    "division": "div",
    "modulus": "mod",
    "bitwise-xor": "xor",
    "bitwise-or": "or",
    "bitwise-and": "and",
    "opposite": "neg",
    "bitwise-negation": "not",
    "lshift": "lshift",
    "rshift": "rshift",
}


def serialize(tacops: List[TACOp]):
    ops_list = [op.to_dict() for op in tacops]
    return [{"proc": "@main", "body": ops_list}]


def pretty_print(tac: TAC) -> str:
    for op in tac.ops:
        if isinstance(op, TACOp):
            print(
               f"\t {op.pretty()}"
            )
        else:
            print(f"{op.name}")

def print_detailed(tac: TAC):
      for op in tac.ops:
        if isinstance(op, TACOp):
            print(
               f"{op.detailed()}"
            )
        else:
            print(f"{op.name}")

# TODO: deserialization
class Lowerer:
    def __init__(self, fn: Function, globals: Dict[str, TACGlobal]):
        self.fn = fn
        self.temporary_counter = 0
        self.label_counter = 1
        self.params = [TACTemp(p[0]) for p in fn.params]
        self.scope_stack = [{p[0]: TACTemp(p[0]) for p in fn.params}]
        self.globals = globals

    def lookup_scope(self, var: str):
        for scope in reversed(self.scope_stack):
            if var in scope:
                return scope[var]
        if var in self.globals:
            return self.globals[var]
        raise Exception(f"Variable {var} undefined")

    def add_var(self, var: str):
        self.scope_stack[-1][var] = TACTemp(var)

    def fresh_temp(self) -> TACTemp:
        var = TACTemp(self.temporary_counter)
        self.temporary_counter += 1
        return var

    def fresh_label(self) -> TACLabel:
        lab = TACLabel(f".L{self.fn.name}.{self.label_counter}")
        self.label_counter += 1
        return lab

    def var_mapping(self, statements: List[Statement]) -> Dict[str, TACTemp]:
        var_to_tmp = {}
        for stmt in statements:
            match stmt:
                case StatementDecl(name, _, _):
                    var_to_tmp[name] = TACTemp(name)
                case _:
                    pass
        return var_to_tmp

    @abstractmethod
    def to_tac(self) -> TAC:
        pass

    def lower(self) -> TACProc:
        return TACProc(self.fn.name, self.to_tac(), self.params)
