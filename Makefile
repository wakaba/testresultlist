all:

data:
	cvs -d /home/cvs co -d data testresults/data
	echo "Next step: chown -R apache.apache data"

## License: Public Domain.
