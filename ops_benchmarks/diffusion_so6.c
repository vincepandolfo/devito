#define _POSIX_C_SOURCE 200809L
#define OPS_2D
#include "stdlib.h"
#include "math.h"
#include "sys/time.h"
#include "ops_seq.h"
#include "diffusion_so2.h"
#include "common_defines.h" 

#define PADDING 6

struct profiler
{
  double section0;
} ;


int Kernel(const int x_M, const int x_m, const int y_M, const int y_m, const float dt, const float h_x, const float h_y, const int time_M, const int time_m, float ** u)
{
  ops_init(0,0,1);
  int range_0[4] = {x_m, x_M, y_m, y_M};
  ops_block block_0 = ops_decl_block(2,"block_0");
  int s2d_ut0_5pt[10] = {0, 1, 1, 0, 0, -1, -1, 0, 0, 0};
  ops_stencil S2D_UT0_5PT = ops_decl_stencil(2,5,(int *)s2d_ut0_5pt,"S2D_UT0_5PT");
  int s2d_ut1_1pt[2] = {0, 0};
  ops_stencil S2D_UT1_1PT = ops_decl_stencil(2,1,(int *)s2d_ut1_1pt,"S2D_UT1_1PT");
  int u_dim[2] = {SIZE, SIZE};
  int u_base[2] = {0, 0};
  int u_d_p[2] = {PADDING, PADDING};
  int u_d_m[2] = {-PADDING, -PADDING};
  ops_dat u_dat[2];
  ops_dat u_dat[0] = ops_decl_dat(block_0,1,(int *)u_dim,(int *)u_base,(int *)u_d_m,(int *)u_d_p,u[0],"float","ut0");
  ops_dat u_dat[1] = ops_decl_dat(block_0,1,(int *)u_dim,(int *)u_base,(int *)u_d_m,(int *)u_d_p,u[1],"float","ut1");
  ops_partition("");
  for (int time = time_m, t0 = (time)%(2), t1 = (time + 1)%(2); time <= time_M; time += 1, t0 = (time)%(2), t1 = (time + 1)%(2))
  {
   /* Begin section0 */
    ops_par_loop(Kernel0,"Kernel0",block_0,2,(int *)range_0,ops_arg_dat(u_dat[t0],1,S2D_UT0_5PT,"float",OPS_READ),ops_arg_dat(u_dat[t1],1,S2D_UT1_1PT,"float",OPS_WRITE),ops_arg_gbl(&dt,1,"float",OPS_READ),ops_arg_gbl(&h_x,1,"float",OPS_READ),ops_arg_gbl(&h_y,1,"float",OPS_READ));
    /* End section0 */
  }
  ops_exit();
  return 0;
}

int main(int argc, char * argv[]) {
  struct profiler timers;

  float ** u = malloc(2 * sizeof(float*));
  size_t grid_size = (SIZE + 2 * PADDING) * (SIZE + 2 * PADDING) * sizeof(float);
  u[0] = malloc(grid_size);
  u[1] = malloc(grid_size);

  memset(u[0], 0, grid_size)
  memset(u[1], 0, grid_size)

  for (int t = 0; t < 2; t++) {
    for (int y = PADDING; y < SIZE + PADDING; y++) {
      for (int x = PADDING; x < SIZE + PADDING; x++) {
        float del_y = ((float) (x - PADDING)) / ((float)SIZE);
        float del_x = ((float) (x - PADDING)) / ((float)SIZE);

        float r = pow(del_y - 0.5, 2) + pow(del_x - 0.5, 2);

        if (0.05 <= r && r <= 0.1) {
          u[t][y * (SIZE + 2 * PADDING) + x] = 1;
        }
      }
    }
  }

  struct timeval start_section0, end_section0;
  gettimeofday(&start_section0, NULL);

  Kernel(SIZE, 0, SIZE, 0, DT, SPACING, SPACING, TIME_M, 0, u);

  gettimeofday(&end_section0, NULL);
  timers.section0 = (double)(end_section0.tv_sec-start_section0.tv_sec)+(double)(end_section0.tv_usec-start_section0.tv_usec)/1000000;

  printf("kernel runtime: %lld\n", timers.section0);

  return 0;
}
