class Batch:
    
    def __init__(self, destination: str, amount: float) -> None:
        self.destination    = destination
        self.amount         = str(amount)
        
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(destination={self.destination}, amount={self.amount})'