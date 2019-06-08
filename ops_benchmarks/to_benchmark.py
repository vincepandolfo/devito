import numpy as np
import sys

from devito import Grid, Eq, Operator, TimeFunction, solve

from opescibench import Benchmark, Executor, RooflinePlotter


def ring_initial(spacing=0.01):
    """Initialise grid with initial condition ("ring")"""
    nx, ny = int(1 / spacing), int(1 / spacing)
    xx, yy = np.meshgrid(np.linspace(0., 1., nx, dtype=np.float32),
                         np.linspace(0., 1., ny, dtype=np.float32))
    ui = np.zeros((nx, ny), dtype=np.float32)
    r = (xx - .5)**2. + (yy - .5)**2.
    ui[np.logical_and(.05 <= r, r <= .1)] = 1.
    return ui


def execute_devito(ui, spacing=0.01, a=0.5, timesteps=500, space_order=2, dse="advanced"):
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
    op = Operator(Eq(u.forward, stencil), dse=dse)

    # Execute the generated Devito stencil operator
    summary = op.apply(u=u, t=timesteps, dt=dt)
    return summary.gflopss, summary.oi, summary.timings


class DiffusionExecutor(Executor):

    def setup(self, **kwargs):
        self.ui = ring_initial(kwargs["spacing"])

    def run(self, *args, **kwargs):
        gflopss, oi, timings = execute_devito(
            self.ui, spacing=kwargs["spacing"],
            timesteps=kwargs["timesteps"], space_order=kwargs["space_order"],
            dse=kwargs["dse"])

        for key in timings.keys():
            self.register(gflopss[key], measure="gflopss", event=key)
            self.register(oi[key], measure="oi", event=key)
            self.register(timings[key], measure="timings", event=key)


if __name__ == "__main__":
    bench = Benchmark(name="Diffusion", resultsdir="res", parameters={
        'timesteps': 1000,
        'spacing': [0.0001, 0.0004],
        'space_order': [4, 8, 12, 16],
        'dse': ["aggressive", "advanced"]
    })

    bench.execute(DiffusionExecutor(), warmups=0, repeats=1)

    """
    Plotting mode to generate plots for performance analysis.
    """
    backend = "ops"
    max_bw = 320
    flop_ceils = [(8228, "ideal peak")]
    resultsdir = "results"

    for dse in ["aggressive", "advanced"]:
        for spacing in [0.0001, 0.0004]:
            params = {
                'dse': dse,
                'spacing': spacing
            }

            gflopss = bench.lookup(params=params, measure="gflopss", event="section0")
            oi = bench.lookup(params=params, measure="oi", event="section0")
            time = bench.lookup(params=params, measure="timings", event="section0")

            # Filename
            shape = int(1 / spacing)
            figname = "Diffusion_[%s,%s]_OPS_dse[%s].pdf" % (shape, shape, dse)

            avail_colors = ['r', 'g', 'b', 'y', 'k', 'm']
            avail_markers = ['o', 'x', '^', 'v', '<', '>']

            used_colors = {}
            used_markers = {}

            # Find min and max runtimes for instances having the same OI
            min_max = {v: [0, sys.maxsize] for v in oi.values()}
            for k, v in time.items():
                i = oi[k]
                min_max[i][0] = v if min_max[i][0] == 0 else min(v, min_max[i][0])
                min_max[i][1] = (v if min_max[i][1] == sys.maxsize
                                 else max(v, min_max[i][1]))

            with RooflinePlotter(figname=figname, plotdir=resultsdir,
                                 max_bw=max_bw, flop_ceils=flop_ceils,
                                 fancycolor=True, legend='drop') as plot:
                for k, v in gflopss.items():
                    so = dict(k)['space_order']

                    oi_value = oi[k]
                    time_value = time[k]
                    label = "SO %s" % so

                    color = used_colors[so] if so in used_colors else avail_colors.pop(0)
                    used_colors.setdefault(so, color)
                    marker = (used_markers[so] if so in used_markers
                              else avail_markers.pop(0))
                    used_markers.setdefault(so, marker)

                    oi_loc = 0.076 if len(str(so)) == 1 else 0.09
                    oi_annotate = {'s': 'SO=%s' % so, 'size': 6, 'xy': (oi_value, oi_loc)}
                    if time_value in min_max[oi_value]:
                        # Only annotate min and max runtimes on each OI line, to avoid
                        # polluting the plot too much
                        point_annotate = {'s': "%.2fs" % time_value, 'xytext': (0.0, 5.5),
                                          'size': 6, 'rotation': 0}
                    else:
                        point_annotate = None
                    oi_line = time_value == min_max[oi_value][0]
                    if oi_line:
                        perf_annotate = {'size': 6, 'xytext': (-4, 5)}

                    plot.add_point(gflops=v, oi=oi_value, marker=marker, color=color,
                                   oi_line=oi_line, label=label,
                                   perf_annotate=perf_annotate,
                                   oi_annotate=oi_annotate, point_annotate=point_annotate)
