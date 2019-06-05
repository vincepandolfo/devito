
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  ut1[OPS_ACC1(0,0)] = -1.25F*(*dt*ut0[OPS_ACC0(0,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,0)]/((*h_y**h_y))) + 6.66666666627862e-1F*(*dt*ut0[OPS_ACC0(0,1)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(1,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,-1)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(-1,0)]/((*h_x**h_x))) - 4.16666666642413e-2F*(*dt*ut0[OPS_ACC0(0,2)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(-2,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(2,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,-2)]/((*h_y**h_y))) + ut0[OPS_ACC0(0,0)];
}
