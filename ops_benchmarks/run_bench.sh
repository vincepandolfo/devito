#!/bin/bash

SPACE_ORDER=$1
OPS_BLOCK_SIZE_X=$2
OPS_BLOCK_SIZE_Y=$3

mkdir build
cp {Makefile,diffusion_so${SPACE_ORDER}.h,diffusion_so${SPACE_ORDER}.c,common_defines.h} build/

cd build

make SPACE_ORDER=$SPACE_ORDER NV_ARCH=Pascal

# collect metrics
nvprof --kernels "ops_Kernel0" --metrics flop_count_sp --metrics flop_count_mp --metrics dram_read_throughput  --metrics dram_write_throughput --metrics dram_read_transactions --metrics dram_write_transactions ./diffusion_so${SPACE_ORDER}_cuda OPS_BLOCK_SIZE_X=${OPS_BLOCK_SIZE_X} OPS_BLOCK_SIZE_Y=${OPS_BLOCK_SIZE_Y}

#timing metrics
nvprof ./diffusion_so${SPACE_ORDER}_cuda OPS_BLOCK_SIZE_X=${OPS_BLOCK_SIZE_X} OPS_BLOCK_SIZE_Y=${OPS_BLOCK_SIZE_Y}

# measure runtime
./diffusion_so${SPACE_ORDER}_cuda OPS_BLOCK_SIZE_X=${OPS_BLOCK_SIZE_X} OPS_BLOCK_SIZE_Y=${OPS_BLOCK_SIZE_Y}


cd ..
rm -rf build

