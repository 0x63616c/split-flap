package main

import "testing"

func TestParseCatalog(t *testing.T) {
	data := []byte(`{"models":{"assembly":"full unit","holder":"flap jig"},` +
		`"printable":["holder"],"src_to_model":{"holder":"holder","params":""}}`)
	c, err := parseCatalog(data)
	if err != nil {
		t.Fatal(err)
	}
	if c.Models["holder"] != "flap jig" || c.Printable[0] != "holder" || c.SrcToModel["holder"] != "holder" {
		t.Fatalf("bad parse: %+v", c)
	}
}

func TestParseCatalogGarbage(t *testing.T) {
	if _, err := parseCatalog([]byte("not json")); err == nil {
		t.Fatal("want error on garbage")
	}
}
