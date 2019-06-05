import numpy as np

from devito import Grid, Eq, Operator, TimeFunction, solve


def ring_initial(spacing=0.01):
    """Initialise grid with initial condition ("ring")"""
    nx, ny = int(1 / spacing), int(1 / spacing)
    xx, yy = np.meshgrid(np.linspace(0., 1., nx, dtype=np.float32),
                         np.linspace(0., 1., ny, dtype=np.float32))
    ui = np.zeros((nx, ny), dtype=np.float32)
    r = (xx - .5)**2. + (yy - .5)**2.
    ui[np.logical_and(.05 <= r, r <= .1)] = 1.
    return ui


def execute_devito(ui, spacing=0.01, a=0.5, timesteps=500, space_order=2):
    """Execute diffusion stencil using the devito Operator API."""
    nx, ny = ui.shape
    dx2, dy2 = spacing**2, spacing**2
    dt = dx2 * dy2 / (2 * a * (dx2 + dy2))
    # Allocate the grid and set initial condition
    # Note: This should be made simpler through the use of defaults
    grid = Grid(shape=(nx, ny))
    u = TimeFunction(name='u', grid=grid, time_order=1, space_order=space_order)
    u.data[0, :] = ui[:]

    # Derive the stencil according to devito conventions
    eqn = Eq(u.dt, a * (u.dx2 + u.dy2))
    stencil = solve(eqn, u.forward)
    op = Operator(Eq(u.forward, stencil))

    # Execute the generated Devito stencil operator
    try:
        op.apply(u=u, t=timesteps, dt=dt)
    except:
        pass


if __name__ == "__main__":
    spacing = 0.0003
    ui = ring_initial(spacing)

    for so in [2, 4, 6, 8, 10, 12, 14, 16]:
        execute_devito(ui, space_order=so)
