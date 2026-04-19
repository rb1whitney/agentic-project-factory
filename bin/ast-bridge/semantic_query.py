import json
import argparse
import sys

class SemanticQuery:
    def __init__(self, graph_file):
        with open(graph_file, "r") as f:
            self.graph = json.load(f)

    def find_definition(self, name):
        node = self.graph["nodes"].get(name)
        if node:
            return f"Definition of '{name}': {node['file']} at line {node['line']} (Type: {node['type']})"
        return f"Symbol '{name}' not found."

    def find_usages(self, name):
        usages = [e for e in self.graph["edges"] if e["to"] == name]
        if not usages:
            return f"No usages found for '{name}'."
        
        res = [f"Usages of '{name}':"]
        for u in usages:
            res.append(f"- Used in {u['from']} (Type: {u['type']})")
        return "\n".join(res)

    def trace_dependencies(self, file_path):
        deps = [e for e in self.graph["edges"] if e["from"] == file_path]
        if not deps:
            return f"No outbound dependencies found for {file_path}."
        
        res = [f"Dependencies of {file_path}:"]
        for d in deps:
            res.append(f"- Depends on {d['to']} (Type: {d['type']})")
        return "\n".join(res)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", default="relationship_graph.json", help="Graph file")
    subparsers = parser.add_subparsers(dest="command")
    
    # def
    p_def = subparsers.add_parser("find-definition")
    p_def.add_argument("name")
    
    # usage
    p_usage = subparsers.add_parser("find-usages")
    p_usage.add_argument("name")
    
    # trace
    p_trace = subparsers.add_parser("trace-dependencies")
    p_trace.add_argument("file")
    
    args = parser.parse_args()
    
    query = SemanticQuery(args.graph)
    if args.command == "find-definition":
        print(query.find_definition(args.name))
    elif args.command == "find-usages":
        print(query.find_usages(args.name))
    elif args.command == "trace-dependencies":
        print(query.trace_dependencies(args.file))
    else:
        parser.print_help()
