from pydantic import BaseModel, Field
from typing import List, Optional

# --- Inventory & Receipt Models ---
class InventoryActionRequest(BaseModel):
    action_type: str
    amount: float
    note: Optional[str] = None

class ApprovedItem(BaseModel):
    id: str
    normalized_name: str
    quantity: float
    included: bool

class ApprovalPayload(BaseModel):
    items: list[ApprovedItem]

class NewItemRequest(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    purchase_date: str

# --- Recommendation Models ---
class RecommendationRequest(BaseModel):
    mealTypes: Optional[List[str]] = []
    maxTotalMinutes: Optional[int] = None
    maxMissingIngredients: Optional[int] = None
    prioritizeIngredients: Optional[List[str]] = []
    excludeIngredients: Optional[List[str]] = []
    dietaryTags: Optional[List[str]] = []
    assumeStaples: bool = True
    limit: int = Field(default=10, le=50)

class ScoreBreakdown(BaseModel):
    pantryCoverage: float
    priorityIngredientUsage: float
    timeFit: float
    optionalCoverage: float

class RecipeResult(BaseModel):
    recipeId: str
    title: str
    score: float
    coveragePercent: float
    totalMinutes: Optional[int]
    matchedRequiredIngredients: List[str]
    missingRequiredIngredients: List[str]
    assumedStaples: List[str]
    missingOptionalIngredients: List[str]
    priorityIngredientsUsed: List[str]
    quantityWarnings: List[str]
    scoreBreakdown: ScoreBreakdown
    explanation: str

class RecommendationResponse(BaseModel):
    algorithmVersion: str = "deterministic-v1"
    generatedAt: str
    pantryItemCount: int
    filters: dict
    results: List[RecipeResult]
    message: Optional[str] = None