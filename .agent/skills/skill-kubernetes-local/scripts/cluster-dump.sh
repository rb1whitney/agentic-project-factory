#!/bin/bash
kubectl get all -A > "cluster-dump.txt"
kubectl get events -A --sort-by='.lastTimestamp' >> "cluster-dump.txt"
