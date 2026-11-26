"""Exact application-configured publisher host bindings, inactive preparation.

No registry entries are shipped here. A caller must obtain the verified domain
configuration through its own authorized process, not model/source assertions.
Binding a host does not prove a page, product, publication date or release fact.
"""
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlsplit


def valid_host(host):
    if type(host) is not str or len(host)>253 or host!=host.lower():return False
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',host) or '.' not in host:return False
    if host.endswith(('.localhost','.local','.internal')):return False
    if any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in host.split('.')):return False
    try:ipaddress.ip_address(host);return False
    except ValueError:return True


@dataclass(frozen=True)
class PublisherBinding:
    publisher_key:str
    hosts:tuple[str,...]


class PublisherRegistry:
    def __init__(self,bindings):
        hosts={}
        for binding in bindings:
            if not isinstance(binding,PublisherBinding) or type(binding.publisher_key) is not str or not binding.publisher_key.strip():raise ValueError('invalid_publisher')
            if type(binding.hosts) is not tuple or not binding.hosts:raise ValueError('invalid_hosts')
            for host in binding.hosts:
                if not valid_host(host) or host in hosts:raise ValueError('invalid_or_duplicate_host')
                hosts[host]=binding.publisher_key
        self._hosts=hosts

    def snapshot(self):
        """Independent validated configuration for a bounded request."""
        return PublisherRegistry(tuple(PublisherBinding(key,(host,)) for host,key in self._hosts.items()))

    def publisher_for(self,url):
        if type(url) is not str or not 0<len(url)<=2048:return None
        if re.search(r'[\x00-\x20\x7f\\]',url) or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|20|7f|5c)',url,re.I):return None
        try:
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.username is not None or parsed.password is not None or parsed.port not in {None,443}:return None
            host=parsed.hostname
            if not valid_host(host):return None
            return self._hosts.get(host)
        except ValueError:return None
