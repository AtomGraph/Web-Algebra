# Web Algebra Formal Semantics

## Abstract Type System

### Primitive Types
```
URI        = Abstract URI reference
Literal    = Abstract literal value with optional datatype and language
BNode      = Abstract blank node identifier
Graph      = Abstract RDF graph
Term       = URI + Literal + BNode
```

### Collection Types
```
Sequence α     = [α]                    -- Ordered list of elements
Result         = SPARQL SELECT result with variables and bindings  
ResultRow      = Single binding row from Result
VariableStack  = [Dict[String, Any]]    -- Stack of variable scopes
Context        = Any                    -- Current execution context (varies by operation)
```

### Operation Types
```
Operation      = Abstract operation that can be executed
Expression     = Operation + Literal + Integer  -- Expressions for filtering
```

## Concrete Python Type System

### RDFLib Types
```python
URI            = rdflib.URIRef
Literal        = rdflib.Literal  
BNode          = rdflib.BNode
Graph          = rdflib.Graph
Term           = Union[rdflib.URIRef, rdflib.Literal, rdflib.BNode]
```

### Collection Types  
```python
Sequence       = List[Any]
Result         = rdflib.query.Result
ResultRow      = rdflib.query.ResultRow
VariableStack  = List[Dict[str, Any]]
Context        = Any
```

### Execution Architecture
```python
# Triple execution pattern - all operations implement:
def execute(*args: RDFLib_types) -> RDFLib_type           # Pure function with RDFLib terms
def execute_json(arguments: dict, variable_stack: list) -> Any  # JSON processing 
def mcp_run(arguments: dict, context: Any = None) -> Any   # MCP interface
```

## Operation Catalog

### Core System Operations

**Value** - Access variables and context values
```
Abstract: String × Context × VariableStack → Any
Python:   def execute(self, name: str, context: Any, variable_stack: List[Dict[str, Any]]) -> Any
```

**Variable** - Set variables in current scope (XSLT-style)
```
Abstract: String × Any × VariableStack → ⊥
Python:   def execute(self, name: str, value: Any, variable_stack: List[Dict[str, Any]]) -> None
```

**Current** - Return current context item
```
Abstract: Any → Any  
Python:   def execute(self, current_item: Any) -> Any
```

**Execute** - Execute nested operation
```
Abstract: Operation → Any
Python:   def execute(self, operation: Any) -> Any
```

**URI** - Convert term to URI reference
```
Abstract: Term → URI
Python:   def execute(self, term: rdflib.term.Node) -> rdflib.URIRef
```

**ForEach** - Map operation over sequence (sequence → sequence semantics)
```
Abstract: Sequence α × Operation → Sequence β
Python:   def execute(self, select_data: Union[List[Any], rdflib.query.Result], operation: Any) -> List[Any]
```

**Filter** - Filter sequences or select from results
```
Abstract: (Sequence α × Expression → α) + (Result × Expression → Result)
Python:   def execute(self, input_data: Any, expression: Any) -> Union[list, Any]
```

**Bindings** - Extract binding sequence from SPARQL results
```
Abstract: Result → Sequence ResultRow
Python:   def execute(self, table: rdflib.query.Result) -> List[Dict[str, Any]]
```

### String Operations

**Str** - Convert any term to string literal
```
Abstract: Term → Literal
Python:   def execute(self, term: rdflib.term.Node) -> rdflib.Literal
```

**Replace** - Replace patterns in strings using regex
```
Abstract: Literal × Literal × Literal → Literal  
Python:   def execute(self, input_str: rdflib.Literal, pattern: rdflib.Literal, replacement: rdflib.Literal) -> rdflib.Literal
```

**EncodeForURI** - URL-encode strings for URI usage
```
Abstract: Literal → Literal
Python:   def execute(self, input_str: Literal) -> Literal
```

**STRUUID** - Generate random UUID string
```
Abstract: () → Literal
Python:   def execute(self) -> Literal
```

### SPARQL Operations

**SELECT** - Execute SPARQL SELECT query
```
Abstract: URI × Literal → Result
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.query.Result
```

**CONSTRUCT** - Execute SPARQL CONSTRUCT query  
```
Abstract: URI × Literal → Graph
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.Graph
```

**DESCRIBE** - Execute SPARQL DESCRIBE query
```
Abstract: URI × Literal → Graph  
Python:   def execute(self, endpoint: rdflib.URIRef, query: rdflib.Literal) -> rdflib.Graph
```

**Substitute** - Replace variables in SPARQL queries
```
Abstract: Literal × Literal × Term → Literal
Python:   def execute(self, query: Literal, var: Literal, binding_value: Any) -> Literal
```

**SPARQLString** - Generate SPARQL queries from natural language
```
Abstract: Literal → Literal
Python:   def execute(self, question: Literal) -> Literal
```

### HTTP Operations

**GET** - Retrieve RDF data via HTTP GET
```
Abstract: URI → Graph
Python:   def execute(self, url: rdflib.URIRef) -> Graph
```

**POST** - Submit RDF data via HTTP POST
```
Abstract: URI × Graph → Result
Python:   def execute(self, url: rdflib.URIRef, data: rdflib.Graph) -> Result
```

**PUT** - Replace RDF data via HTTP PUT
```
Abstract: URI × Graph → Result
Python:   def execute(self, url: rdflib.URIRef, data: rdflib.Graph) -> Result
```

**PATCH** - Update RDF data via HTTP PATCH with SPARQL Update
```
Abstract: URI × Literal → Result
Python:   def execute(self, url: URIRef, update: Literal) -> Result
```

### LinkedDataHub Operations

**ldh-CreateContainer** - Create LinkedDataHub container document
```
Abstract: URI × Literal × Maybe Literal × Maybe Literal → Result
Python:   def execute(self, parent_uri: rdflib.URIRef, title: rdflib.Literal, slug: rdflib.Literal = None, description: rdflib.Literal = None) -> Result
```

**ldh-CreateItem** - Create LinkedDataHub item document  
```
Abstract: URI × Literal × Maybe Literal → Result
Python:   def execute(self, container_uri: rdflib.URIRef, title: rdflib.Literal, slug: Optional[rdflib.Literal] = None) -> Result
```

**ldh-List** - List LinkedDataHub resources
```
Abstract: URI × URI → List[Dict]
Python:   def execute(self, url: URIRef, endpoint: URIRef) -> list[dict]
```

**ldh-AddView** - Add view to LinkedDataHub document
```
Abstract: URI × URI × Literal × Maybe Literal × Maybe Literal × Maybe URI → Any  
Python:   def execute(self, url: URIRef, query: URIRef, title: Literal, description: Literal = None, fragment: Literal = None, mode: URIRef = None) -> Any
```

**ldh-AddResultSetChart** - Add result set chart to LinkedDataHub document
```
Abstract: URI × URI × Literal × URI × Literal × Literal × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, query: URIRef, title: Literal, chart_type: URIRef, category_var_name: Literal, series_var_name: Literal, description: Literal = None, fragment: Literal = None) -> Any
```

**ldh-AddSelect** - Add SPARQL SELECT service to LinkedDataHub
```
Abstract: URI × Literal × Literal × Maybe Literal × Maybe Literal × Maybe URI → Any
Python:   def execute(self, url: URIRef, query: Literal, title: Literal, description: Literal = None, fragment: Literal = None, service: URIRef = None) -> Any
```

**ldh-AddGenericService** - Add generic SPARQL service to LinkedDataHub
```
Abstract: URI × URI × Literal × Maybe Literal × Maybe Literal × Maybe URI × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, endpoint: URIRef, title: Literal, description: Literal = None, fragment: Literal = None, graph_store: URIRef = None, auth_user: Literal = None, auth_pwd: Literal = None) -> Any
```

**ldh-AddObjectBlock** - Add object content block to LinkedDataHub document
```
Abstract: URI × URI × Maybe Literal × Maybe Literal × Maybe Literal × Maybe URI → Any
Python:   def execute(self, url: URIRef, value: URIRef, title: Literal = None, description: Literal = None, fragment: Literal = None, mode: URIRef = None) -> Any
```

**ldh-AddXHTMLBlock** - Add XHTML content block to LinkedDataHub document  
```
Abstract: URI × Literal × Maybe Literal × Maybe Literal × Maybe Literal → Any
Python:   def execute(self, url: URIRef, value: Literal, title: Literal = None, description: Literal = None, fragment: Literal = None) -> Any
```

**ldh-RemoveBlock** - Remove content block from LinkedDataHub document
```
Abstract: URI × Maybe URI → Any  
Python:   def execute(self, url: URIRef, block: URIRef = None) -> Any
```

### Schema Operations

**ExtractClasses** - Extract RDF classes from graph
```
Abstract: URI → Graph
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
```

**ExtractDatatypeProperties** - Extract datatype properties from graph
```
Abstract: URI → Graph  
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
```

**ExtractObjectProperties** - Extract object properties from graph
```
Abstract: URI → Graph
Python:   def execute(self, endpoint: URIRef) -> rdflib.Graph
```

### Utility Operations

**Merge** - Merge multiple RDF graphs into one
```
Abstract: Sequence Graph → Graph
Python:   def execute(self, graphs: List[rdflib.Graph]) -> rdflib.Graph
```

**ResolveURI** - Resolve relative URI against base URI
```
Abstract: URI × Literal → URI
Python:   def execute(self, base: URIRef, relative: Literal) -> URIRef
```

## Type System Properties

### Strict Type Checking
- All operations enforce strict input type checking
- TypeError raised for mismatched input types with informative messages
- No automatic type casting or conversion
- RDFLib types must match exactly as specified in signatures

### Execution Architecture
- **execute()**: Pure functions operating on RDFLib types only
- **execute_json()**: JSON processing layer that calls execute() with type validation
- **mcp_run()**: MCP interface layer that calls execute() with plain arguments

### Sequence Semantics  
- **ForEach**: Maps from sequences to sequences (sequence → sequence)
- **Context**: In ForEach, context is the current sequence item (ResultRow for JSONResult)
- **Filter**: Can operate on both sequences and JSONResult tables
- **Automatic Application**: Single-item operations applied element-wise to sequences in execution layer

### Variable System
- **Lexical Scoping**: Variables follow XSLT-style lexical scoping rules
- **Variable Stack**: Maintains nested scopes for variable resolution
- **Syntax**: `$variableName` for variable references, `variableName` for context access
- **Variable**: Sets variables in current scope, Variable operation manages the stack

### Context System
- **Context Type**: `Any` - varies by operation and execution context
- **ForEach Context**: Current sequence item (ResultRow for SPARQL results)
- **Current Operation**: Returns the current context item unchanged
- **Value Operation**: Accesses both context values and variables from stack

### URI Resolution
- **JSON-LD Parsing**: All operations that parse JSON-LD use `base` parameter to resolve relative URIs
- **Fragment URIs**: Fragment identifiers like `#service` resolve against target document URI
- **Base URI**: Set to the target document URI for correct resolution of relative references
- **Implementation**: Uses `rdflib.Graph.parse(data=json_data, format="json-ld", base=target_url)`