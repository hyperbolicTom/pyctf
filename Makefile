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

clean: clean-x
