from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .costs import CostController,UsageRecord
from .distributed import DistributedExecutor
from .economics import CompanyEconomics,Opportunity,PortfolioDecision
from .reliability import ReliabilityController
from .redteam import RedTeamCase,RedTeamReport,RedTeamValidator
@dataclass
class ProductionCompanyControl:
    distributed:DistributedExecutor
    economics:CompanyEconomics
    costs:CostController
    reliability:ReliabilityController
    redteam:RedTeamValidator
    def prioritize(self,items:list[Opportunity],budget:Decimal)->PortfolioDecision: return self.economics.prioritize(items,budget)
    def authorize_cost(self,project_id:str,estimate:Decimal)->bool: return self.costs.authorize(project_id,estimate)
    def record_cost(self,actor:str,project_id:str,input_tokens:int,output_tokens:int,cost:Decimal)->None: self.costs.record(UsageRecord(actor,project_id,input_tokens,output_tokens,cost))
    def run_redteam(self,cases:list[RedTeamCase],policy)->RedTeamReport: return self.redteam.evaluate(cases,policy)
    def health(self)->dict[str,object]: return {"workers":self.distributed.health(),"reliability":self.reliability.health()}
