 
FROM python:3-alpine

# Getting things ready
WORKDIR /usr/src/tim
COPY Pipfile.lock Pipfile ./

# Install dependencies & configure machine
ARG GF_UID="500"
ARG GF_GID="500"
RUN apk update && \
	apk add gettext curl bash && \
	apk add --no-cache postgresql-libs && \
	apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
	pip install pipenv && \
	pipenv install --system --deploy && \
	apk --purge del .build-deps && \
	rm -rf /var/lib/apt/lists/* && \
	rm /var/cache/apk/* && \
	addgroup --system -g $GF_GID appgroup && \
	adduser appuser --system --uid $GF_UID -G appgroup

# Install Shynet
COPY tim .
RUN python manage.py collectstatic --noinput

# Launch
USER appuser
EXPOSE 8080
ENTRYPOINT [ "./entrypoint.sh" ]