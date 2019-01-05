include ../config/Makefile.config

all:

install: all
	@mkdir -p $(LIBDIR)
	@mkdir -p $(BINDIR)
	cp thd_atr.py $(LIBDIR)
	cp StockwellDs.py StockwellProj.py disptfbrik.py disptfband.py $(BINDIR)
	cp -r matlab $(BINDIR)

clean:
	rm -f *~ *.pyc *.o *.a *.so

