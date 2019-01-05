include ../config/Makefile.config

all: project.so

project.so: project.c
	env PYMODNAME=project PYMODLIBS="" $(MAKE) -f $(CONFDIR)/Makefile.pymod

install: all
	@mkdir -p $(BINDIR)
	cp *.py $(BINDIR)

clean:
	rm -f *~ *.pyc *.o *.a *.so

