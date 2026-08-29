from pydantic import BaseModel
from typing import List, Optional

# --- Inventory & Receipt Models (Day 7) ---

class InventoryActionRequest(BaseModel):
    action_type: str
    amount: float
    unit: Optional[str] = None
    note: Optional[str] = None

class NewItemRequest(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    purchase_date: Optional[str] = None

class ReceiptItemDraft(BaseModel):
    normalized_name: str
    quantity: float
    included: bool

class ApprovalPayload(BaseModel):
    items: List[ReceiptItemDraft]


# --- Recommendation Models (Day 9 & 10) ---

class RecommendationRequest(BaseModel):
    queryText: Optional[str] = None
    mealTypes: Optional[List[str]] = []
    maxTotalMinutes: Optional[int] = None
    maxMissingIngredients: Optional[int] = None
    prioritizeIngredients: Optional[List[str]] = []
    excludeIngredients: Optional[List[str]] = []
    assumeStaples: Optional[bool] = True
    limit: Optional[int] = 5

class RecommendationResult(BaseModel):
    recipeId: str
    title: str
    totalMinutes: Optional[int] = 0
    deterministicScore: float
    semanticScore: Optional[float] = None
    hybridScore: Optional[float] = None
    coveragePercent: float
    matchedRequiredIngredients: List[str]
    missingRequiredIngredients: List[str]
    assumedStaples: List[str]
    deterministicExplanation: str
    aiExplanation: Optional[str] = None
    sourceName: str

class RecommendationResponse(BaseModel):
    algorithmVersion: str
    retrievalMode: str
    queryText: Optional[str] = None
    pantryItemCount: int
    results: List[RecommendationResult]


# --- User Action & Feedback Models (Day 11) ---

class SaveRecipeRequest(BaseModel):
    recommendationRunId: Optional[str] = None

class DismissRecipeRequest(BaseModel):
    reason: Optional[str] = None
    note: Optional[str] = None

class RecipeFeedbackRequest(BaseModel):
    recommendationRunId: Optional[str] = None
    actionType: str
    reason: Optional[str] = None
    note: Optional[str] = None


# --- Cooking Workflow Models (Day 11) ---

class DeductionItem(BaseModel):
    pantryItemId: str
    recipeIngredientId: Optional[str] = None
    quantity: float
    unit: str

class CookingCompleteRequest(BaseModel):
    idempotencyKey: str
    recommendationRunId: Optional[str] = None
    deductions: List[DeductionItem]