# ADR-006: AI/ML Model Integration Strategy

## Status
Proposed

## Context
We need to define our AI/ML integration strategy for:
- Natural language understanding of part descriptions
- Translating descriptions to CAD operations
- Optimization suggestions for designs
- Intent detection for abuse prevention
- Template parameter recommendations

This is a **critical** decision as it directly impacts the core user experience.

## Decision
We will use a **hybrid approach** combining:
1. **OpenAI GPT-4** (or equivalent) for natural language understanding
2. **Structured output parsing** to convert NL to CAD operations
3. **Rule-based post-processing** for CAD-specific constraints
4. **Custom fine-tuned models** for intent detection (future)

Technology choices:
- **LLM Provider**: OpenAI API (GPT-4o/GPT-4-turbo)
- **Framework**: LangChain for orchestration
- **Structured Output**: Pydantic models with function calling
- **Embeddings**: OpenAI embeddings for semantic search (templates)
- **Fallback**: Claude API as backup provider

## Consequences

### Positive
- **Rapid development**: Leverage state-of-the-art models without training
- **High quality NLU**: GPT-4 excels at understanding complex descriptions
- **Structured outputs**: Function calling ensures parseable responses
- **Flexibility**: Can swap providers or add local models later
- **Semantic search**: Embeddings enable intelligent template matching

### Negative
- **API costs**: Per-token pricing can add up
- **Latency**: API calls add 1-5 seconds to generation
- **Vendor dependency**: Reliant on OpenAI availability
- **Rate limits**: May hit limits under high load
- **Privacy considerations**: User prompts sent to external API

### Risk Mitigation
- Implement caching for common patterns
- Use Claude as fallback provider
- Design for eventual local model support
- Rate limit user requests
- Anonymize sensitive data in prompts

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **OpenAI GPT-4 + LangChain** | Best NLU, structured output, fast to implement | Cost, latency, vendor lock | ⭐⭐⭐⭐⭐ |
| OpenAI + custom orchestration | Full control | More development work | ⭐⭐⭐⭐ |
| Anthropic Claude only | Good NLU, longer context | Less structured output maturity | ⭐⭐⭐⭐ |
| Local LLM (Llama, Mistral) | Privacy, no API costs | Lower quality, infrastructure | ⭐⭐⭐ |
| Custom trained model | Domain-specific | Expensive, long development | ⭐⭐ |

## Technical Details

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                                │
│  "Create a box 100x50x30mm with rounded corners and lid"    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Service Layer                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  1. Input Validation & Preprocessing                    ││
│  │     - Sanitize input                                    ││
│  │     - Check for prohibited content (fast filter)        ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  2. Template Matching (Semantic Search)                 ││
│  │     - Embed input                                       ││
│  │     - Find similar templates                            ││
│  │     - Confidence threshold check                        ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  3. LLM Parsing (GPT-4 + Function Calling)             ││
│  │     - Parse description to structured CAD operations    ││
│  │     - Extract dimensions, features, constraints         ││
│  │     - Validate output schema                            ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  4. Post-Processing & Validation                        ││
│  │     - Apply CAD constraints                             ││
│  │     - Validate dimensions                               ││
│  │     - Generate warnings                                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAD Operation Plan                        │
│  {                                                           │
│    "template": "project_box",                               │
│    "parameters": {                                          │
│      "length": 100, "width": 50, "height": 30,             │
│      "corner_radius": 5, "include_lid": true               │
│    },                                                        │
│    "confidence": 0.92                                        │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Pydantic Models for Structured Output
```python
# app/services/ai/schemas.py
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class ShapeType(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CONE = "cone"
    CUSTOM = "custom"

class Feature(BaseModel):
    type: Literal["hole", "fillet", "chamfer", "slot", "boss", "pocket"]
    parameters: dict
    location: Optional[dict] = None

class CADOperationPlan(BaseModel):
    """Structured output from LLM for CAD generation."""
    
    template_match: Optional[str] = Field(
        None, 
        description="Name of matching template if applicable"
    )
    base_shape: ShapeType = Field(
        description="Primary shape type"
    )
    dimensions: dict = Field(
        description="Key dimensions in mm (length, width, height, diameter, etc.)"
    )
    features: list[Feature] = Field(
        default_factory=list,
        description="Additional features to add"
    )
    modifiers: dict = Field(
        default_factory=dict,
        description="Global modifiers (fillet_all_edges, shell_thickness, etc.)"
    )
    material_hint: Optional[str] = Field(
        None,
        description="Material hint for defaults (PLA, PETG, etc.)"
    )
    confidence: float = Field(
        ge=0, le=1,
        description="Confidence in interpretation"
    )
    clarification_needed: Optional[str] = Field(
        None,
        description="Question to ask user if interpretation unclear"
    )
```

### LangChain Integration
```python
# app/services/ai/llm_service.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .schemas import CADOperationPlan

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,  # Low for consistent output
        )
        self.parser = PydanticOutputParser(pydantic_object=CADOperationPlan)
        self.prompt = self._build_prompt()
    
    def _build_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert CAD engineer assistant. 
Your job is to interpret natural language descriptions of 3D parts and convert them 
to structured CAD operation plans.

Available templates: {templates}

Guidelines:
- Always output dimensions in millimeters
- If a template matches, use it with parameters
- For custom shapes, break down into base shape + features
- Express confidence 0-1 based on clarity of description
- If ambiguous, set clarification_needed

{format_instructions}"""),
            ("human", "{description}")
        ])
    
    async def parse_description(
        self, 
        description: str,
        available_templates: list[str]
    ) -> CADOperationPlan:
        """Parse a natural language description into CAD operations."""
        
        chain = self.prompt | self.llm | self.parser
        
        result = await chain.ainvoke({
            "description": description,
            "templates": ", ".join(available_templates),
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result
```

### Function Calling Alternative
```python
# Using OpenAI function calling directly
from openai import AsyncOpenAI

client = AsyncOpenAI()

CAD_FUNCTIONS = [
    {
        "name": "create_cad_operation_plan",
        "description": "Convert a part description to CAD operations",
        "parameters": CADOperationPlan.model_json_schema()
    }
]

async def parse_with_functions(description: str) -> CADOperationPlan:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description}
        ],
        functions=CAD_FUNCTIONS,
        function_call={"name": "create_cad_operation_plan"}
    )
    
    args = json.loads(response.choices[0].message.function_call.arguments)
    return CADOperationPlan(**args)
```

### Optimization Suggestions
```python
# app/services/ai/optimizer.py
class DesignOptimizer:
    """Generate optimization suggestions for designs."""
    
    async def analyze(self, geometry_metadata: dict) -> list[Suggestion]:
        prompt = f"""Analyze this 3D printable part and suggest optimizations:

Geometry:
- Volume: {geometry_metadata['volume_mm3']} mm³
- Bounding box: {geometry_metadata['bounding_box']}
- Min wall thickness: {geometry_metadata['min_wall_thickness']} mm
- Max overhang: {geometry_metadata['max_overhang']}°

Provide suggestions for:
1. Printability improvements
2. Structural improvements  
3. Material efficiency

Format as JSON array of suggestions."""
        
        response = await self.llm.complete(prompt)
        return parse_suggestions(response)
```

### Content Moderation
```python
# app/services/ai/moderation.py
from openai import AsyncOpenAI

class ContentModerator:
    """Detect prohibited content in design requests."""
    
    PROHIBITED_CATEGORIES = [
        "weapons", "weapon_components", "firearms", 
        "explosives", "illegal_items"
    ]
    
    async def check(self, description: str) -> ModerationResult:
        # Fast keyword check first
        if self._keyword_check(description):
            return ModerationResult(blocked=True, reason="prohibited_keyword")
        
        # OpenAI moderation API
        moderation = await self.client.moderations.create(
            input=description
        )
        
        if moderation.results[0].flagged:
            return ModerationResult(blocked=True, reason="content_policy")
        
        # Custom intent classification
        intent = await self._classify_intent(description)
        if intent.category in self.PROHIBITED_CATEGORIES:
            if intent.confidence > 0.8:
                return ModerationResult(blocked=True, reason=intent.category)
            elif intent.confidence > 0.5:
                return ModerationResult(
                    blocked=False, 
                    requires_review=True,
                    reason=intent.category
                )
        
        return ModerationResult(blocked=False)
```

### Cost Estimation
| Operation | Model | Est. Tokens | Cost per 1K |
|-----------|-------|-------------|-------------|
| Parse description | GPT-4o | ~500 | ~$0.005 |
| Optimization suggestions | GPT-4o | ~800 | ~$0.008 |
| Template matching (embedding) | text-embedding-3-small | ~100 | ~$0.00002 |

**Estimated cost per design generation**: $0.01-0.02

## POC Validation Tasks
- [ ] Implement basic description parsing with GPT-4
- [ ] Test structured output with 20+ example descriptions
- [ ] Measure latency for typical requests
- [ ] Evaluate template matching accuracy
- [ ] Test content moderation with edge cases

## Future Considerations
- Fine-tune smaller model on CAD-specific data
- Add Claude as fallback for reliability
- Implement local inference for cost reduction at scale
- Caching layer for common patterns

## References
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI Moderation](https://platform.openai.com/docs/guides/moderation)
