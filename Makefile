all:
	docker compose up -d

build:	
	docker compose up -d --build

down:
	docker compose down

fclean: down
	docker stop $(docker ps -q) || true
	docker system prune --all --force --volumes
	docker network prune --force
	docker volume prune --force