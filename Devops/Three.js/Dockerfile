FROM node:alpine

WORKDIR /usr/src/app

COPY start.sh /

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]

CMD ["npm", "start"]