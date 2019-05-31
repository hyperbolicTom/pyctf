include config/Makefile.config

# Use "make install" to install into the directory specified in config/Makefile.config.
# Use "make symlinks" to additionally create symbolic links in DESTBIN and DESTLIB.

DESTBIN = $(HOME)/bin
DESTLIB = $(HOME)/lib

targets = pyctf parsemarks avghc StockwellDs filterDs projDs thresholdDetect fiddist

all:
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

install: all
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

symlinks: install
	mkdir -p $(DESTBIN)
	mkdir -p $(DESTLIB)
	@for x in $(BINDIR)/*.py $(BINDIR)/parsemarks $(BINDIR)/matlab ; do \
		y=`basename $$x` ; \
		echo ln -s -f $$x $(DESTBIN)/$$y ; \
		ln -s -f $$x $(DESTBIN)/$$y ; \
	done
	ln -s -f $(LIBDIR) $(DESTLIB)

clean: clean-x
