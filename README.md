# pyoptsparsewrapper

A simplified pyOptSparse interface.  Mainly for students in my optimization class.

The dictionary-based format in pyoptsparse is very convenient when dealing with large problems where the gradients or linear constraints have significant sparsity.  But for smaller problems putting arrays in and out of dictionaries can be cumbersome.

Other additions include:
- combining obj/con and gradient functions without extra function calls.
- making the availability of xStar and fStar clear (as return objects)
- fixing a bug where fStar isn't updated for some optimizers
- fixing a bug in NLPQLP xStar output
- returning number of function calls correctly
- automatically check if gradients are supplied or not
- automatically determining size of design vars, constraints, etc.
- convenient syntax for defining linear constraints.

Syntax is similar to Matlab's fmincon, except the linear constraints are optional arguments:

`xopt, fopt, info = optimize(func, x0, lb, ub, optimizer, A=[], b=[], Aeq=[], beq=[])`

See example.py for usage.
