import sys
from lib.asmgen import AsmGen
from lib.parser import parser
from lib.checker import pp_errs, check_programm
from lib.bmm import bmm
from lib.tac import var_mapping
if __name__ == "__main__":
    with open(sys.argv[1]) as fp:
        source = fp.read()
    ast = parser.parse(source)
    errs = check_programm(ast)
    if errs != []:
        pp_errs(errs)
        sys.exit()
    
    vars_to_tmp = var_mapping(ast.stmts)
    tac = bmm(ast.stmts, vars_to_tmp)

    asm_gen = AsmGen(tac)

    print(asm_gen.compile())