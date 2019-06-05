
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  float r0 = 1.0F / *h_y**h_y;
  float r1 = 1.0F / *h_x**h_x;
  ut1[OPS_ACC1(0,0)] = -1.49138888879679F*(*dt*ut0[OPS_ACC0(0,0)]*r1 + *dt*ut0[OPS_ACC0(0,0)]*r0) + 8.57142857159488e-1F*(*dt*ut0[OPS_ACC0(-1,0)]*r1 + *dt*ut0[OPS_ACC0(1,0)]*r1 + *dt*ut0[OPS_ACC0(0,-1)]*r0 + *dt*ut0[OPS_ACC0(0,1)]*r0) - 1.33928571420256e-1F*(*dt*ut0[OPS_ACC0(-2,0)]*r1 + *dt*ut0[OPS_ACC0(2,0)]*r1 + *dt*ut0[OPS_ACC0(0,-2)]*r0 + *dt*ut0[OPS_ACC0(0,2)]*r0) + 2.64550264546415e-2F*(*dt*ut0[OPS_ACC0(-3,0)]*r1 + *dt*ut0[OPS_ACC0(3,0)]*r1 + *dt*ut0[OPS_ACC0(0,-3)]*r0 + *dt*ut0[OPS_ACC0(0,3)]*r0) - 4.4642857146755e-3F*(*dt*ut0[OPS_ACC0(-4,0)]*r1 + *dt*ut0[OPS_ACC0(4,0)]*r1 + *dt*ut0[OPS_ACC0(0,-4)]*r0 + *dt*ut0[OPS_ACC0(0,4)]*r0) + 5.1948051952877e-4F*(*dt*ut0[OPS_ACC0(-5,0)]*r1 + *dt*ut0[OPS_ACC0(5,0)]*r1 + *dt*ut0[OPS_ACC0(0,-5)]*r0 + *dt*ut0[OPS_ACC0(0,5)]*r0) - 3.00625300617696e-5F*(*dt*ut0[OPS_ACC0(-6,0)]*r1 + *dt*ut0[OPS_ACC0(6,0)]*r1 + *dt*ut0[OPS_ACC0(0,-6)]*r0 + *dt*ut0[OPS_ACC0(0,6)]*r0) + ut0[OPS_ACC0(0,0)];
}
