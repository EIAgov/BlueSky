from collections import defaultdict
import pyomo.environ as pyo

a = pyo.ConcreteModel()

meta = pyo.ConcreteModel()

meta.a = a

# ensure we can alter it after incorporation...

a.S = pyo.Set(initialize=[1, 2, 3])
a.x = pyo.Var(a.S)
meta.pprint()  # works!


@a.Constraint(a.S)
def limit(m, s):
    return m.x[s] >= 3


a.obj = pyo.Objective(expr=sum(a.x[s] for s in a.S))

# test that a defaultdict works to gather an expression...
d = defaultdict(float)
d[44] += a.x[2] + 8

for v in d.values():
    print(v)  # works!


# trying to find out where the darn dual is in a block/submodel
meta.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
a.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

opt = pyo.SolverFactory('appsi_highs')
res = opt.solve(meta)
print('sub duals')
print(list(k.name for k in a.dual.keys()))
print('meta duals')
print(list(k.name for k in meta.dual.keys()))

print(pyo.value(meta.dual[a.limit[2]]))  # bingo

# meta.del_component(a)
# meta.pprint()
