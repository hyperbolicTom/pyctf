include config/Makefile.config

targets = pyctf parsemarks avghc StockwellDs filterDs projDs thresholdDetect fiddist

all:
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

install: all
	for x in $(targets) ; do \
		$(MAKE) -C $$x $@ || exit ;\
	done

install-home: all
	for x in $(targets) ; do \
		env BINDIR=~/bin LIBDIR=~/lib/pyctf $(MAKE) -e -C $$x install || exit ;\
	done

clean: clean-x
