package main

import (
	"fmt"
	"net"
	"testing"
)

func TestFreePortSkipsBusy(t *testing.T) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	busy := l.Addr().(*net.TCPAddr).Port
	got, err := freePort(busy)
	if err != nil {
		t.Fatal(err)
	}
	if got == busy {
		t.Fatalf("returned busy port %d", busy)
	}
	if got < busy {
		t.Fatalf("scanned backwards: %d < %d", got, busy)
	}
	l2, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", got))
	if err != nil {
		t.Fatalf("returned port not actually free: %v", err)
	}
	l2.Close()
}
