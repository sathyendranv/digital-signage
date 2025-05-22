import importlib.metadata
from datetime import datetime


class Version_sch(object):
    """
    Version schema to describe a component's version information."""
    component:str=None
    version:str=None
    observation:str=None
    lastverification:str=None

class PcaServerMetadata:
    """
    Metadata for PCA Server.
    """
    __version__ = "0.1.0"
    __name_short = "PCA Server"
    __name_extended = "Product Consumption Analyzer (PCA) Server"
    __description_short = "It analyzes product consumption probabilities based on sales transactions and on-the-fly object detections (MQTT)."

    @staticmethod
    def version():
        return PcaServerMetadata.__version__
    
    @staticmethod
    def name_short():
        return PcaServerMetadata.__name_short

    @staticmethod
    def name_extended():
        return PcaServerMetadata.__name_extended

    @staticmethod
    def description_short():
        return PcaServerMetadata.__description_short

    @staticmethod
    def get_pca_versioninfo() -> Version_sch:
        pcaversion = Version_sch()
        pcaversion.component = PcaServerMetadata.name_short()
        pcaversion.version = PcaServerMetadata.version()
        pcaversion.observation = PcaServerMetadata.description_short()
        pcaversion.lastverification = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return pcaversion

class ServerEnvironment:
    @staticmethod
    def get_dependencies() -> list[Version_sch]:
        """
        Get the PCA dependencies and their versions.
        """
        dependencies = []
        for dist in importlib.metadata.distributions():
                dep = Version_sch()
                dep.component = dist.metadata['Name']
                dep.version = dist.version
                dep.observation = dist.metadata['Summary']
                dep.lastverification = datetime.now().strftime("%Y-%m-%d %H:%M")
                dependencies.append(dep)        
        return dependencies

        
    
    @staticmethod
    def get_pca_with_dependencies() -> list[Version_sch]:
        """
        Get the PCA version and dependencies.
        """
        pca = PcaServerMetadata.get_pca_versioninfo()
        dependencies = ServerEnvironment.get_dependencies()
        return [pca] + dependencies
