from .bxast import *
from typing import Dict


@dataclass
class TACTemp:
    num: int

    def __str__(self):
        return f"%{self.num}"

    def __eq__(self, __value: object) -> bool:
        return self.num == __value.num


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
    args: List[TACTemp | TACLabel | int]
    result: TACTemp | None

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
        return (
            f"{self.result} = {self.opcode} {' '.join([str(arg) for arg in self.args])}"
        )


@dataclass
class TAC:
    ops: List[TACOp | TACLabel]

    def get_tmps(self):
        temps = set()
        for op in self.ops:
            if isinstance(op, TACOp):
                for arg in op.args:
                    match arg:
                        case TACTemp(n):
                            temps.add(n)
                        case _:
                            pass
                if op.result is not None:
                    temps.add(op.result.num)
        return temps


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
                f"\t {op.result} = {op.opcode} {' '.join([str(arg) for arg in op.args])}"
            )
        else:
            print(f"{op.name}")


# TODO: deserialization
class Lowerer:
    def __init__(self, fn: Function):
        self.fn = fn
        self.temporary_counter = 0
        self.label_counter = 1
        self.scope_stack = [{}]

    def lookup_scope(self, var: str):
        for scope in reversed(self.scope_stack):
            if var in scope:
                return scope[var]
        raise Exception(f"Variable {var} undefined")

    def add_var(self, var: str):
        self.scope_stack[-1][var] = self.fresh_temp()

    def fresh_temp(self) -> TACTemp:
        var = TACTemp(self.temporary_counter)
        self.temporary_counter += 1
        return var

    def fresh_label(self) -> TACLabel:
        lab = TACLabel(f".L{self.label_counter}")
        self.label_counter += 1
        return lab

    def var_mapping(self, statements: List[Statement]) -> Dict[str, TACTemp]:
        var_to_tmp = {}
        for stmt in statements:
            match stmt:
                case StatementDecl(name, _, _):
                    var_to_tmp[name] = self.fresh_temp()
                case _:
                    pass
        return var_to_tmp

    @abstractmethod
    def to_tac(self):
        pass
