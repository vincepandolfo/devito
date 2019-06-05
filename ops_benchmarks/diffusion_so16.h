
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  float r0 = 1.0F / *h_y**h_y;
  float r1 = 1.0F / *h_x**h_x;
  ut1[OPS_ACC1(0,0)] = -1.52742205210961F*(*dt*ut0[OPS_ACC0(0,0)]*r1 + *dt*ut0[OPS_ACC0(0,0)]*r0) + 8.88888888875954e-1F*(*dt*ut0[OPS_ACC0(-1,0)]*r1 + *dt*ut0[OPS_ACC0(1,0)]*r1 + *dt*ut0[OPS_ACC0(0,-1)]*r0 + *dt*ut0[OPS_ACC0(0,1)]*r0) - 1.55555555567844e-1F*(*dt*ut0[OPS_ACC0(-2,0)]*r1 + *dt*ut0[OPS_ACC0(2,0)]*r1 + *dt*ut0[OPS_ACC0(0,-2)]*r0 + *dt*ut0[OPS_ACC0(0,2)]*r0) + 3.77104377112119e-2F*(*dt*ut0[OPS_ACC0(-3,0)]*r1 + *dt*ut0[OPS_ACC0(3,0)]*r1 + *dt*ut0[OPS_ACC0(0,-3)]*r0 + *dt*ut0[OPS_ACC0(0,3)]*r0) - 8.8383838392474e-3F*(*dt*ut0[OPS_ACC0(-4,0)]*r1 + *dt*ut0[OPS_ACC0(4,0)]*r1 + *dt*ut0[OPS_ACC0(0,-4)]*r0 + *dt*ut0[OPS_ACC0(0,4)]*r0) + 1.74048174039854e-3F*(*dt*ut0[OPS_ACC0(-5,0)]*r1 + *dt*ut0[OPS_ACC0(5,0)]*r1 + *dt*ut0[OPS_ACC0(0,-5)]*r0 + *dt*ut0[OPS_ACC0(0,5)]*r0) - 2.59000259006825e-4F*(*dt*ut0[OPS_ACC0(-6,0)]*r1 + *dt*ut0[OPS_ACC0(6,0)]*r1 + *dt*ut0[OPS_ACC0(0,-6)]*r0 + *dt*ut0[OPS_ACC0(0,6)]*r0) + 2.53714539439898e-5F*(*dt*ut0[OPS_ACC0(-7,0)]*r1 + *dt*ut0[OPS_ACC0(7,0)]*r1 + *dt*ut0[OPS_ACC0(0,-7)]*r0 + *dt*ut0[OPS_ACC0(0,7)]*r0) - 1.21406371400568e-6F*(*dt*ut0[OPS_ACC0(-8,0)]*r1 + *dt*ut0[OPS_ACC0(8,0)]*r1 + *dt*ut0[OPS_ACC0(0,-8)]*r0 + *dt*ut0[OPS_ACC0(0,8)]*r0) + ut0[OPS_ACC0(0,0)];
}
