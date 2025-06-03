from . import constants

def global_constants(request):
    return {
        k: v for k, v in vars(constants).items()
        if k.isupper() and not k.startswith("_")
    }
