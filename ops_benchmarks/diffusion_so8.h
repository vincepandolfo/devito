
void Kernel0(const float * ut0, float * ut1, const float *dt, const float *h_x, const float *h_y)
{
  ut1[OPS_ACC1(0,0)] = -1.42361111100763F*(*dt*ut0[OPS_ACC0(0,0)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(0,0)]/((*h_x**h_x))) + 8.00000000046566e-1F*(*dt*ut0[OPS_ACC0(-1,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(1,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,1)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(0,-1)]/((*h_y**h_y))) + 1.26984126982279e-2F*(*dt*ut0[OPS_ACC0(0,-3)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(3,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,3)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(-3,0)]/((*h_x**h_x))) - 1.00000000005821e-1F*(*dt*ut0[OPS_ACC0(0,2)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(0,-2)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(-2,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(2,0)]/((*h_x**h_x))) - 8.9285714284415e-4F*(*dt*ut0[OPS_ACC0(0,4)]/((*h_y**h_y)) + *dt*ut0[OPS_ACC0(-4,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(4,0)]/((*h_x**h_x)) + *dt*ut0[OPS_ACC0(0,-4)]/((*h_y**h_y))) + ut0[OPS_ACC0(0,0)];
}
