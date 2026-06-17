.PHONY: build run test clean tidy

BINARY := lclreason
CMD    := ./cmd/lclreason

build:
	go build -o $(BINARY) $(CMD)

run: build
	./$(BINARY) --mode coordinator

worker: build
	./$(BINARY) --mode worker

test:
	go test ./...

tidy:
	go mod tidy

clean:
	rm -f $(BINARY) lclreason.db

# Cross-compile targets
build-linux:
	GOOS=linux GOARCH=amd64 go build -o $(BINARY)-linux-amd64 $(CMD)

build-arm64:
	GOOS=linux GOARCH=arm64 go build -o $(BINARY)-linux-arm64 $(CMD)

build-mac:
	GOOS=darwin GOARCH=arm64 go build -o $(BINARY)-darwin-arm64 $(CMD)
