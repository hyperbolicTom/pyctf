include ../../config/Makefile.config

all: st.so

st.so: st.c
	env PYMODNAME=st PYMODCFLAGS="" PYMODLIBS="-lfftw3" $(MAKE) -f $(CONFDIR)/Makefile.pymod

stomp.so: stomp.c
	env PYMODNAME=stomp PYMODCFLAGS="-fopenmp" PYMODLIBS="-lfftw3" $(MAKE) -f $(CONFDIR)/Makefile.pymod

DEST = $(LIBDIR)/st

install: all
	@mkdir -p $(DEST)
	cp st.so *.py $(DEST)

clean:	clean-x
