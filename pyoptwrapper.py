from pyoptsparse import Optimization
import warnings
import numpy as np


def optimize(func, x0, lb, ub, optimizer, A=[], b=[], Aeq=[], beq=[], args=[]):

    global fcalls  # keep track of function calls myself, seems to be an error in pyopt
    fcalls = 1

    # evalute initial point to get size information and determine if gradients included
    out = func(x0, *args)
    if len(out) == 6:
        gradients = True
        f, c, ceq, _, _, _ = out
    else:
        gradients = False
        f, c, ceq = out

    nx = len(x0)
    nc = len(c)
    nceq = len(ceq)
    nlin = len(b)
    nleq = len(beq)
    if hasattr(f, "__len__"):
        nf = len(f)  # multiobjective
    else:
        nf = 1


    def objcon(xdict):

        global fcalls
        fcalls += 1

        x = xdict['x']
        outputs = {}

        if gradients:
            f, c, ceq, df, dc, dceq = func(x, *args)
            # these gradients aren't directly used in this function but we will save them for later
            outputs['g-obj'] = df
            outputs['g-con'] = dc
            outputs['g-con-eq'] = dceq
            outputs['g-x'] = x
        else:
            f, c, ceq = func(x, *args)

        outputs['con'] = c
        outputs['con-eq'] = ceq

        if nf == 1:
            outputs['obj'] = f
        else:  # multiobjective
            for i in range(nf):
                outputs['obj%d' % i] = f[i]

        fail = False

        return outputs, fail


    def grad(xdict, fdict):

        # check if this was the x-location we just evaluated from func (should never happen)
        if not np.array_equal(xdict['x'], fdict['g-x']):
            f, c, ceq, df, dc, dceq = func(xdict['x'], *args)
            global fcalls
            fcalls += 1
        else:
            df = fdict['g-obj']
            dc = fdict['g-con']
            dceq = fdict['g-con-eq']

        # populate gradients (the multiobjective optimizers don't use gradients so no change needed here)
        gout = {}
        gout['obj'] = {}
        gout['obj']['x'] = df
        gout['con'] = {}
        gout['con']['x'] = dc
        gout['con-eq'] = {}
        gout['con-eq']['x'] = dceq

        fail = False

        return gout, fail




    # setup problem
    optProb = Optimization('optimization', objcon)

    if nf == 1:
        optProb.addObj('obj')
    else:  # multiobjective
        for i in range(nf):
            optProb.addObj('obj%d' % i)

    optProb.addVarGroup('x', nx, lower=lb, upper=ub, value=x0)

    # add nonlinear constraints
    if nc > 0:
        optProb.addConGroup('con', nc, upper=0.0)

    if nceq > 0:
        optProb.addConGroup('con-eq', nceq, upper=0.0, lower=0.0)

    # add linear inequality constraints
    if nlin > 0:
        optProb.addConGroup('linear-ineq', nlin, upper=b, linear=True, jac={'x': A})

    # add linear equality constraints
    if nleq > 0:
        optProb.addConGroup('linear-ineq', nleq, upper=beq, lower=beq, linear=True, jac={'x': Aeq})

    # check if gradients defined
    if gradients:
        sens = grad
    else:
        sens = 'FDR'  # forward diff with relative step size

    with warnings.catch_warnings():  # FIXME: ignore the FutureWarning until fixed
        warnings.simplefilter("ignore")

        # run optimization
        sol = optimizer(optProb, sens=sens)


    # save solution
    xstar = sol.xStar['x']
    fstar = sol.fStar

    info = {}
    info['fcalls'] = fcalls
    info['time'] = sol.optTime
    if sol.optInform:
        info['code'] = sol.optInform

    # FIXME: bug in how output of NLPQLP is returned
    if optimizer.name == 'NLPQLP':
        xtemp = xstar
        xstar = np.zeros(nx)
        for i in range(nx):
            xstar[i] = xtemp[i, 0]

    # FIXME: because of bug exists in all except SNOPT, also none return cstar
    # if optimizer.name != 'SNOPT':
    if gradients:
        fstar, cstar, ceqstar, _, _, _ = func(xstar, *args)
    else:
        fstar, cstar, ceqstar = func(xstar, *args)

    # FIXME: handle multiobjective NSGA2
    if nf > 1 and optimizer.name == 'NSGA-II':
        xstar = []
        fstar = []
        cstar = []
        # TODO: currently it ignores equality constraints.
        with open('nsga2_final_pop.out') as f:
            # skip first two lines
            f.readline()
            f.readline()
            for line in f:
                values = line.split()
                rank = values[nx + nc + nf + 1]
                if rank == "1":
                    fstar.append(np.array(values[:nf]).astype(np.float))
                    cstar.append(np.array(values[nf:nf+nc]).astype(np.float))
                    xstar.append(np.array(values[nf+nc:nf+nc+nx]).astype(np.float))

        xstar = np.array(xstar)
        fstar = np.array(fstar)
        cstar = -np.array(cstar)  # negative sign because of nsga definition

    max_c_vio = 0.0
    if nc > 0:
        max_c_vio = max(np.amax(cstar), max_c_vio)
    if nceq > 0:
        max_c_vio = max(np.amax(np.abs(ceqstar)), max_c_vio)
    info['max-c-vio'] = max_c_vio

    return xstar, fstar, info
