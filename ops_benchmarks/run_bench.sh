#!/bin/bash

SPACE_ORDER=$1

mkdir build
cp {Makefile,diffusion_so${SPACE_ORDER}.h,diffusion_so${SPACE_ORDER}.c,common_defines.h} build/

cd build

make SPACE_ORDER=$SPACE_ORDER NV_ARCH=Pascal

# collect metrics
nvprof --kernels "ops_Kernel0" --metrics flop_count_sp --metrics flop_count_mp --metrics dram_read_throughput  --metrics dram_write_throughput --metrics dram_read_transactions --metrics dram_write_transactions ./diffusion_so${SPACE_ORDER}_cuda

# measure runtime
./diffusion_so${SPACE_ORDER}_cuda


cd ..
rm -rf build

