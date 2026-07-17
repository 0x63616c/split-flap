package main

import (
	"fmt"
	"net"
)

// freePort returns the first free TCP port on 127.0.0.1 at or above `from`.
func freePort(from int) (int, error) {
	for p := from; p < from+100; p++ {
		l, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", p))
		if err != nil {
			continue
		}
		l.Close()
		return p, nil
	}
	return 0, fmt.Errorf("no free port in %d-%d", from, from+99)
}
