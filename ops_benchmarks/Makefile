#
# The following environment variables should be predefined:
#
# OPS_INSTALL_PATH
# OPS_COMPILER (gnu,intel,etc)
#

include $(OPS_INSTALL_PATH)/../makefiles/Makefile.common
include $(OPS_INSTALL_PATH)/../makefiles/Makefile.mpi
include $(OPS_INSTALL_PATH)/../makefiles/Makefile.cuda
include $(OPS_INSTALL_PATH)/../makefiles/Makefile.hdf5



HEADERS=diffusion_so$(SPACE_ORDER).h

OPS_FILES=diffusion_so$(SPACE_ORDER).c

OPS_GENERATED=diffusion_so$(SPACE_ORDER)_ops.cpp

OTHER_FILES=


APP=diffusion_so$(SPACE_ORDER)
MAIN_SRC=diffusion_so$(SPACE_ORDER)

include $(OPS_INSTALL_PATH)/../makefiles/Makefile.c_app

