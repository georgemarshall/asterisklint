from ..base import FuncBase


class FAXOPT(FuncBase):
    pass


def register(func_loader):
    func_loader.register(FAXOPT())
