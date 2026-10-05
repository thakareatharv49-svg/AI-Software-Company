from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
@dataclass(frozen=True)
class Opportunity: id:str; name:str; value:Decimal; cost:Decimal; strategic_fit:Decimal; risk:Decimal
@dataclass(frozen=True)
class PortfolioDecision: selected:tuple[str,...]; total_value:Decimal; total_cost:Decimal; rationale:str
class CompanyEconomics:
    def score(self,item:Opportunity)->Decimal:
        if item.cost<0 or item.risk<0: raise ValueError("cost and risk cannot be negative")
        return item.value+item.strategic_fit-item.cost-item.risk
    def prioritize(self,items:list[Opportunity],budget:Decimal)->PortfolioDecision:
        if budget<0: raise ValueError("budget cannot be negative")
        ordered=sorted(items,key=self.score,reverse=True); selected=[]; cost=Decimal("0"); value=Decimal("0")
        for item in ordered:
            if cost+item.cost<=budget and self.score(item)>0: selected.append(item.id); cost+=item.cost; value+=item.value
        return PortfolioDecision(tuple(selected),value,cost,"Selected positive-score opportunities within budget.")
