from decimal import Decimal
from company.economics import CompanyEconomics,Opportunity
def op(i,v,c,s,r): return Opportunity(i,i,Decimal(v),Decimal(c),Decimal(s),Decimal(r))
def test_prioritize_with_budget():
    result=CompanyEconomics().prioritize([op("a","10","3","4","1"),op("b","8","2","1","1"),op("c","1","1","0","2")],Decimal("5"))
    assert result.selected==("a","b")
    assert result.total_cost==Decimal("5")
