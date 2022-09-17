FROM quay.io/wakaba/docker-perl-app-base

ADD . /app/

RUN cd /app && \
    make deps-docker PMBP_OPTIONS="--execute-system-package-installer --dump-info-file-before-die" && \
    echo '#!/bin/bash' > /server && \
    echo 'export LANG=C' >> /server && \
    echo 'export TZ=UTC' >> /server && \
    echo 'port=${PORT:-8080}' >> /server && \
    echo 'cd /app && ./plackup -p ${port} -s Twiggy::Prefork bin/server.psgi' >> /server && \
    chmod u+x /server && \
    rm -rf /var/lib/apt/lists/* /app/local/pmbp/tmp /app/deps

CMD ["/server"]

## License: Public Domain.
