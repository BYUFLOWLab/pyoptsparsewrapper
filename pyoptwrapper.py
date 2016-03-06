from pyoptsparse import Optimization
import warnings
import numpy as np


def optimize(func, x0, lb, ub, optimizer, A=[], b=[], Aeq=[], beq=[]):

    global fcalls  # keep track of function calls myself, seems to be an error in pyopt
    fcalls = 1

    # evalute initial point to get size information and determine if gradients included
    out = func(x0)
    if len(out) == 4:
        gradients = True
        f, c, _, _ = out
    else:
        gradients = False
        f, c = out

    nx = len(x0)
    nc = len(c)
    nlin = len(b)
    nleq = len(beq)


    def objcon(xdict):

        global fcalls
        fcalls += 1

        x = xdict['x']
        outputs = {}

        if gradients:
            f, c, df, dc = func(x)
            # these gradients aren't directly used in this function but we will save them for later
            outputs['g-obj'] = df
            outputs['g-con'] = dc
            outputs['g-x'] = x
        else:
            f, c = func(x)

        outputs['obj'] = f
        outputs['con'] = c

        fail = False

        return outputs, fail


    def grad(xdict, fdict):

        # check if this was the x-location we just evaluated from func (should never happen)
        if not np.array_equal(xdict['x'], fdict['g-x']):
            f, c, df, dc = func(xdict['x'])
            global fcalls
            fcalls += 1
        else:
            df = fdict['g-obj']
            dc = fdict['g-con']

        # populate gradients
        gout = {}
        gout['obj'] = {}
        gout['obj']['x'] = df
        gout['con'] = {}
        gout['con']['x'] = dc

        fail = False

        return gout, fail




    # setup problem
    optProb = Optimization('optimization', objcon)
    optProb.addObj('obj')
    optProb.addVarGroup('x', nx, lower=lb, upper=ub, value=x0)

    # add nonlinear constraints
    if nc > 0:
        optProb.addConGroup('con', nc, upper=0.0)

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
    info['code'] = sol.optInform

    # FIXME: bug in how output of NLPQLP is returned
    if optimizer.name == 'NLPQLP':
        xtemp = xstar
        xstar = np.zeros(nx)
        for i in range(nx):
            xstar[i] = xtemp[i, 0]

    # FIXME: because of bug exists in all except SNOPT
    if optimizer.name != 'SNOPT':
        if gradients:
            fstar, cstar, _, _ = func(xstar)
        else:
            fstar, cstar = func(xstar)

    return xstar, fstar, info
