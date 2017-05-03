from sympy import Eq
from sympy.abc import h, s

from devito import Operator, Forward, Backward, t, time


def ForwardOperator(model, u, src, rec, time_order=2, spc_order=6,
                    save=False, u_ini=None, **kwargs):
    """
    Constructor method for the forward modelling operator in an acoustic media

    :param model: :class:`Model` object containing the physical parameters
    :param source: None or IShot() (not currently supported properly)
    :param data: IShot() object containing the acquisition geometry and field data
    :param: time_order: Time discretization order
    :param: spc_order: Space discretization order
    :param save : Saving flag, True saves all time steps, False only the three
    :param: u_ini : wavefield at the three first time step for non-zero initial condition
     required for the time marching scheme
    """
    m, damp = model.m, model.damp

    # Derive stencil from symbolic equation
    if time_order == 2:
        laplacian = u.laplace
        biharmonic = 0
        # PDE for information
        # eqn = m * u.dt2 - laplacian + damp * u.dt
        dt = model.critical_dt
    else:
        laplacian = u.laplace
        biharmonic = u.laplace2(1/m)
        # PDE for information
        # eqn = m * u.dt2 - laplacian - s**2 / 12 * biharmonic + damp * u.dt
        dt = 1.73 * model.critical_dt

    # Create the stencil by hand instead of calling numpy solve for speed purposes
    # Simple linear solve of a u(t+dt) + b u(t) + c u(t-dt) = L for u(t+dt)
    stencil = 1 / (2 * m + s * damp) * (
        4 * m * u + (s * damp - 2 * m) * u.backward +
        2 * s**2 * (laplacian + s**2 / 12 * biharmonic))
    # Add substitutions for spacing (temporal and spatial)
    subs = {s: dt, h: model.get_spacing()}

    dse = kwargs.get('dse', 'advanced')
    dle = kwargs.get('dle', 'advanced')

    # Create stencil expression
    eqn = Eq(u.forward, stencil)

    # Construct expression to inject source values
    # Note that src and field terms have differing time indices:
    #   src[time, ...] - always accesses the "unrolled" time index
    #   u[ti + 1, ...] - accesses the forward stencil value
    ti = u.indices[0]
    source = src.inject(field=u.indexed[ti + 1, ...], offset=model.nbpml,
                        expr=src.indexed[time, ...] * dt * dt / m)

    # Create interpolation expression for receivers
    receivers = Eq(rec, rec.interpolate(expr=u, offset=model.nbpml))

    return Operator(stencils=[eqn] + source + [receivers],
                    subs=subs, dse=dse, dle=dle,
                    time_axis=Forward, name="Forward")


def AdjointOperator(model, v, srca, rec, time_order=2, spc_order=6,
                    save=False, u_ini=None, **kwargs):
    """
    Class to setup the adjoint modelling operator in an acoustic media

    :param model: :class:`Model` object containing the physical parameters
    :param source: None or IShot() (not currently supported properly)
    :param data: IShot() object containing the acquisition geometry and field data
    :param: time_order: Time discretization order
    :param: spc_order: Space discretization order
    """
    m, damp = model.m, model.damp

    # Derive stencil from symbolic equation
    if time_order == 2:
        laplacian = v.laplace
        biharmonic = 0
        # PDE for information
        # eqn = m * u.dt2 - laplacian + damp * u.dt
        dt = model.critical_dt
    else:
        laplacian = v.laplace
        biharmonic = v.laplace2(1/m)
        # PDE for information
        # eqn = m * u.dt2 - laplacian - s**2 / 12 * biharmonic + damp * u.dt
        dt = 1.73 * model.critical_dt

    # Create the stencil by hand instead of calling numpy solve for speed purposes
    # Simple linear solve of a u(t+dt) + b u(t) + c u(t-dt) = L for u(t+dt)
    stencil = 1 / (2 * m + s * damp) * (
        4 * m * v + (s * damp - 2 * m) * v.forward +
        2 * s**2 * (laplacian + s**2 / 12 * biharmonic))
    # Add substitutions for spacing (temporal and spatial)
    subs = {s: dt, h: model.get_spacing()}

    dse = kwargs.get('dse', 'advanced')
    dle = kwargs.get('dle', 'advanced')

    # Create stencil expressions for operator, source and receivers
    eqn = Eq(v.backward, stencil)

    # Construct expression to inject receiver values
    ti = v.indices[0]
    receivers = rec.inject(field=v.indexed[ti - 1, ...], offset=model.nbpml,
                           expr=rec.indexed[time, ...] * dt * dt / m)

    # Create interpolation expression for the adjoint-source
    source_a = Eq(srca, srca.interpolate(expr=v, offset=model.nbpml))

    return Operator(stencils=[eqn] + receivers + [source_a],
                    subs=subs, dse=dse, dle=dle,
                    time_axis=Backward, name="Adjoint")


def GradientOperator(model, v, grad, rec, u, time_order=2, spc_order=6,
                     **kwargs):
    """
    Class to setup the gradient operator in an acoustic media

    :param model: :class:`Model` object containing the physical parameters
    :param src: None ot IShot() (not currently supported properly)
    :param data: IShot() object containing the acquisition geometry and field data
    :param: recin : receiver data for the adjoint source
    :param: time_order: Time discretization order
    :param: spc_order: Space discretization order
    """
    m, damp = model.m, model.damp

    # Derive stencil from symbolic equation
    if time_order == 2:
        laplacian = v.laplace
        biharmonic = 0
        # PDE for information
        # eqn = m * v.dt2 - laplacian - damp * v.dt
        dt = model.critical_dt

        gradient_update = Eq(grad, grad - u.dt2 * v)
    else:
        laplacian = v.laplace
        biharmonic = v.laplace2(1/m)
        biharmonicu = - u.laplace2(1/(m**2))
        # PDE for information
        # eqn = m * v.dt2 - laplacian - s**2 / 12 * biharmonic + damp * v.dt
        dt = 1.73 * model.critical_dt
        gradient_update = Eq(grad, grad -
                             (u.dt2 -
                              s ** 2 / 12.0 * biharmonicu) * v)

    # Create the stencil by hand instead of calling numpy solve for speed purposes
    # Simple linear solve of a v(t+dt) + b u(t) + c v(t-dt) = L for v(t-dt)
    stencil = 1.0 / (2.0 * m + s * damp) * \
        (4.0 * m * v + (s * damp - 2.0 * m) *
         v.forward + 2.0 * s ** 2 * (laplacian + s**2 / 12.0 * biharmonic))
    # Add substitutions for spacing (temporal and spatial)
    subs = {s: dt, h: model.get_spacing()}
    # Add Gradient-specific updates. The dt2 is currently hacky
    #  as it has to match the cyclic indices

    dse = kwargs.get('dse', 'advanced')
    dle = kwargs.get('dle', 'advanced')

    # Create stencil expressions for operator
    eqn = Eq(v.backward, stencil)

    # Add expression for receiver injection
    ti = v.indices[0]
    receivers = rec.inject(field=v.indexed[ti - 1, ...], offset=model.nbpml,
                           expr=rec.indexed[time, ...] * dt * dt / m)

    return Operator(stencils=[eqn] + [gradient_update] + receivers,
                    subs=subs, dse=dse, dle=dle,
                    time_axis=Backward, name="Gradient")


def BornOperator(model, u, U, src, rec, dm, time_order=2, spc_order=6,
                 **kwargs):
    """
    Class to setup the linearized modelling operator in an acoustic media

    :param model: :class:`Model` object containing the physical parameters
    :param src: None ot IShot() (not currently supported properly)
    :param data: IShot() object containing the acquisition geometry and field data
    :param: dmin : square slowness perturbation
    :param: recin : receiver data for the adjoint source
    :param: time_order: Time discretization order
    :param: spc_order: Space discretization order
    """
    m, damp = model.m, model.damp

    # Derive stencils from symbolic equation
    if time_order == 2:
        laplacianu = u.laplace
        biharmonicu = 0
        laplacianU = U.laplace
        biharmonicU = 0
        dt = model.critical_dt
    else:
        laplacianu = u.laplace
        biharmonicu = u.laplace2(1/m)
        laplacianU = U.laplace
        biharmonicU = U.laplace2(1/m)
        dt = 1.73 * model.critical_dt
        # first_eqn = m * u.dt2 - u.laplace + damp * u.dt
        # second_eqn = m * U.dt2 - U.laplace - dm* u.dt2 + damp * U.dt

    stencil1 = 1.0 / (2.0 * m + s * damp) * \
        (4.0 * m * u + (s * damp - 2.0 * m) *
         u.backward + 2.0 * s ** 2 * (laplacianu + s**2 / 12 * biharmonicu))
    stencil2 = 1.0 / (2.0 * m + s * damp) * \
        (4.0 * m * U + (s * damp - 2.0 * m) *
         U.backward + 2.0 * s ** 2 * (laplacianU +
                                      s**2 / 12 * biharmonicU - dm * u.dt2))
    # Add substitutions for spacing (temporal and spatial)
    subs = {s: dt, h: model.get_spacing()}

    dse = kwargs.get('dse', None)
    dle = kwargs.get('dle', None)

    # Create stencil expressions for operator, source and receivers
    eqn1 = Eq(u.forward, stencil1)
    eqn2 = Eq(U.forward, stencil2)

    # Add source term expression for u
    source = src.inject(field=u.indexed[t + 1, ...], offset=model.nbpml,
                        expr=src.indexed[time, ...] * dt * dt / m)

    # Create receiver interpolation expression from U
    receivers = Eq(rec, rec.interpolate(expr=U, offset=model.nbpml))

    return Operator(stencils=[eqn1] + source + [eqn2] + [receivers],
                    subs=subs, dse=dse, dle=dle,
                    time_axis=Forward, name="Born")
