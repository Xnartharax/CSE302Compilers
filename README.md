# CSE302Compilers

Team - Antonia Baies, Aarrya Saraf, and Jonas Treplin. \
Project: Register Allocation. \
Labs and the project for CSE302 compilers 


## How to run

The compiler functionality is in `main.py` a basic compile command would be:

```
python main.py examples/benchmark.bx -o examples/benchmark
```

The command syntax is `python main.py file`. An optional `-o path` determines the names of the outputs `path.o` and `path.S`. 
If not specified this defaults to `out`.  

Additionally, we provide different optimization levels that can be specified with `-O[level]` like in GCC. The default Level is `O0` These levels include:

O0: No optimization is done we go straight SRC -> AST -> TAC -> ASM. Every variable is spilled by default. This is seen as the most reliable compilation to see if the compiler is correct.   
O1: In this case the compilation procedure goes SRC ->AST -> TAC -> CFG -> TAC -> ASM. In the CFG stage, we only perform block coalescing and unconditional jump threading. Also, we run liveness analysis, but it is used for nothing in this optimization step.  
O2:  This optimisation level introduces SSA and SSA minimization the pipeline goes SRC ->AST -> TAC -> CFG -> SSA -> TAC -> ASM. In SSA form we perform rename and null choice elimination but no copy propagation (thus the more complex SSA deserialization is not needed). Also, we add conditional jump threading in the CFG step.   
O3: In this optimization level we add register allocation (SRC ->AST -> TAC -> CFG -> SSA -> TAC -> ETAC -> ASM).  The register allocation is run on the deconstructed TAC.  
O4: This level only adds only two final optimizations: copy propagation in the SSA phase and register coalescing in the allocation step. 

Overall we observe about a 40% gain in runtime when moving from O0 to O4 on our benchmark.bx file.

## Liveness Analysis and SSA Construction

The code to compute liveness information on a TAC CFG can be found in `lib/liveness.py`. It is implemented in the `LivenessAnalyzer` class and follows the procedure outlined in the lecture straightforwardly.

All the code related to SSA construction is found in `lib/ssa.py`. The class `SSACrudeGenerator` implements the procedure outlined in the lecture:

1. For each block insert phony definitions for all live-in instructions
2. Append a version to each variable which is increased each time it is written to 
3. Convert the phony definitions into proper phi instructions using the last version of each predecessor block.

Since we use a different datastructure for SSA than TAC we also need to replace the predecessor and successor blocks in the meantime. 

We use the `SSALivenessAnalyzer` in `lib/liveness.py` to annotate liveness information to the SSA form again. This could probably done a bit simpler if we just carry over and properly rename the liveness info in the construction step.

## SSA Optimization

All optimization in the SSA Form is done in `SSAOptimizer` in `lib/ssa.py`. We have 3 optimizations:

1. Copy Propagation: A copy in SSA form `%1.n = copy %0.m` can be replaced by globally renaming `%1.n` as `%0.m`. This is rather straightforward to do and only requires only one single pass.
2. Null choice elimination and rename simplification. These are used in union: each time we perform all possible rename simplifications we follow up by eliminating all null choice phis. This goes on until we can't find any renames anymore.

## SSA Deconstruction

The deconstruction is implemented in `SSADeconstructor` in `lib/ssa.py`. This performs the advanced deconstruction technique outlined in the lecture:

Every `%x.0 = phi (L1 : %y1.v1, ..., Ln: %yn.vn)` gets converted into a `%x.0 = copy %yi.vi` at the end of the `Li` block in random order. If we have any circular copies that could lead to dangerous undesired overrides we detect this and insert a dummy variable to break the cycle as outlined in the lecture for unconventional SSA destruction.

Also, we rename all the versioned SSATemps into regular unversioned TACTemps.

## Register Allocation

### Compute the Interference Graph

Represented temporaries by nodes storing the name, value (only for Max Cardinality Search), and the list of neighbors. The class can be seen in `lib/alloc.py` Then the total graph is a dictionary from the name of a temp to such nodes. A dictionary with no neighbors was created and then based on the livein, def, etc we created sets of which temps appeared together and added the neighbors accordingly. This can be found in `lib/mcs.py`.

### Use Max Cardinality Search to find a Simplicial Elimination Ordering 

Applied the given algorithm by updating the value count of the elements in the dictionary. This can be found in `lib/mcs.py`.

### Use Greedy Coloring on the SEO

Applies the given algorithm and spits out a dictionary with the temps as keys and colors as values. The fixed registers are the six input parameters. This can be found in `lib/greedy_coloring.py`.


### If needing >13 colors spill some temporaries and redo from step 2
A function checks if there are more than 13 colors. If no it returns no, but if yes it randomly picks a node and returns it. In the allocation, if a node is returned then we remove it from the InterferenceGraph and try again. Hence this uses a remove function in the Interference Graph, updates the stack size, and repeats the process from step 2. This can be found in `lib/greedy_coloring.py`.

### Finally, compute the allocation record

Here we only need to convert the elementary dicts into explicit data structures that integrate well into the global project structure.
Register allocation is done on the deconstructed TAC but is implemented in a way that it is possible to also do it in SSA form. In this case, one only needs to remember to call `SSADeconstructor.rename_alloc` to rename the SSA Temps in the Allocation Record to their regular TAC form.

## Register Coalescing 

According to the given algorithm, checks for conditions, and merges two temporaries in the Interference Graph using the marge nodes function. This can be found in `lib/greedy_coloring.py`.

## Assembly generation

Allocated assembly generation is handled by `AllocAsmGen` in `lib/asmgen2.py` unallocated assembly can be generated by `AsmGen` in `lib/asmgen.py` or by using the `SpillingAllocator` in `lib/alloc.py`.

Usually, all instructions translate quite easily from the simple case into the allocated case with only a few extra cases to be added when optimizations can be done such as using the same register for the input and output of an add or mul instruction when it can be overridden.

Where we really add extra complication is in the calling convention since we have to pay attention to the caller and callee-save registers. Thus we need to push all callee-save registers that are used at the beginning of the function and restore them at the end and we have to push all caller-save registers that need to stay alive when we call a function and restore them afterwards. This is further complicated by the need to maintain stac alignment. Also, we need to avoid overriding when we have any temporary stored in any of the parameter registers. This is done by pushing them onto the stack before we call the function. Also, the way we set up the interference graph construction we add dummy variables such that no variable that needs to stay alive over a call is allocated to one of the param registers. But this may be a bit strong restrictions so we implemented the assembly generation such that we could remove it.

## ! Extra Experimental !: SCCP Optimization

Implemented SCCP from the dataflow project proposal. The code can be found in `lib/dataflow.py`. The SCCP can be activated using the `-O5` option. In addition to the static computations outlined in the project proposal we can also handle a bit more complex cases like: 
1. Identities like `%x = add %y 0` or `%x = div %y 1` are treated as copies (i.e. replaced by renames).
2. We can also interpret `%x = sub %y %y` as `%x = const 0`.
3. Divisions or multiplications by a power of 2 are optimized to shifts.
A real improvement comes when we combine the static jump evaluation with block coalescing after this step. This will then really get rid of long jump chains that are now statically known. We can reduce the example of `examples/bigcondition2.bx` to just a simple call to print using this. If you want to combine SCCP with Register allocation you need to use `-O6`. This required some changes in the assembly generation to be able to handle instructions with constants in them in all cases but is otherwise a drop-in module.

## Tying it all together

All these conversion and optimization steps are tied together in `lib/compile.py`. Where one can see the process for compiling one function in `compile_unit`.
