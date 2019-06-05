
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  float r0 = 1.0F / *h_y**h_y;
  float r1 = 1.0F / *h_x**h_x;
  ut1[OPS_ACC1(0,0)] = -1.51179705210961F*(*dt*ut0[OPS_ACC0(0,0)]*r1 + *dt*ut0[OPS_ACC0(0,0)]*r0) + 8.75e-1F*(*dt*ut0[OPS_ACC0(-1,0)]*r1 + *dt*ut0[OPS_ACC0(1,0)]*r1 + *dt*ut0[OPS_ACC0(0,-1)]*r0 + *dt*ut0[OPS_ACC0(0,1)]*r0) - 1.45833333343035e-1F*(*dt*ut0[OPS_ACC0(-2,0)]*r1 + *dt*ut0[OPS_ACC0(2,0)]*r1 + *dt*ut0[OPS_ACC0(0,-2)]*r0 + *dt*ut0[OPS_ACC0(0,2)]*r0) + 3.24074074087548e-2F*(*dt*ut0[OPS_ACC0(-3,0)]*r1 + *dt*ut0[OPS_ACC0(3,0)]*r1 + *dt*ut0[OPS_ACC0(0,-3)]*r0 + *dt*ut0[OPS_ACC0(0,3)]*r0) - 6.6287878789808e-3F*(*dt*ut0[OPS_ACC0(-4,0)]*r1 + *dt*ut0[OPS_ACC0(4,0)]*r1 + *dt*ut0[OPS_ACC0(0,-4)]*r0 + *dt*ut0[OPS_ACC0(0,4)]*r0) + 1.06060606071878e-3F*(*dt*ut0[OPS_ACC0(-5,0)]*r1 + *dt*ut0[OPS_ACC0(5,0)]*r1 + *dt*ut0[OPS_ACC0(0,-5)]*r0 + *dt*ut0[OPS_ACC0(0,5)]*r0) - 1.13312613308381e-4F*(*dt*ut0[OPS_ACC0(-6,0)]*r1 + *dt*ut0[OPS_ACC0(6,0)]*r1 + *dt*ut0[OPS_ACC0(0,-6)]*r0 + *dt*ut0[OPS_ACC0(0,6)]*r0) + 5.9464345181226e-6F*(*dt*ut0[OPS_ACC0(-7,0)]*r1 + *dt*ut0[OPS_ACC0(7,0)]*r1 + *dt*ut0[OPS_ACC0(0,-7)]*r0 + *dt*ut0[OPS_ACC0(0,7)]*r0) + ut0[OPS_ACC0(0,0)];
}
