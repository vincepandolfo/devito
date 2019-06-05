
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  float r0 = 1.0F / (*h_y**h_y);
  float r1 = 1.0F / (*h_x**h_x);
  ut1[OPS_ACC1(0,0)] = -1.0F*(*dt*ut0[OPS_ACC0(0,0)]*r1 + *dt*ut0[OPS_ACC0(0,0)]*r0) + 5.0e-1F*(*dt*ut0[OPS_ACC0(-1,0)]*r1 + *dt*ut0[OPS_ACC0(1,0)]*r1 + *dt*ut0[OPS_ACC0(0,-1)]*r0 + *dt*ut0[OPS_ACC0(0,1)]*r0) + ut0[OPS_ACC0(0,0)];
}
