%global commitid 4016ad4
%global serial 10
# Copyright (c) 2000-2009, JPackage Project
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of the JPackage Project nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

%{?scl:%scl_package %{?scl_prefix}mod_cluster-native}
%{!?scl:%global pkg_name %{name}}


#no jars in this native build, so skip signing
%define _jarsign_opts --nocopy

%define reltag .Final
%define namedversion %{version}%{reltag}
%define jarname mod-cluster
%define aplibdir %{_libdir}/httpd/modules/

%if "%{?rhel}" == "6"
%bcond_without zip
%else
%bcond_with zip
%endif

Name:		%{?scl_prefix}mod_cluster-native
Summary: 	JBoss mod_cluster for Apache httpd
Version: 	1.3.1
Release: 	11%{?dist}
Epoch:		0
License: 	LGPLv3
Group: 		Applications/System
URL:		http://www.jboss.org/
# git clone git://git.app.eng.bos.redhat.com/mod_cluster.git
# cd mod_cluster && git checkout 1.3.1.Final-redhat-2
#HEAD is now at 4016ad4... apply patch for CVE-2015-0298
# rm -fr .git .gitignore
# cd ../ && mv mod_cluster mod_cluster-1.3.1.Final
# tar czf mod_cluster-1.3.1.Final.tar.gz mod_cluster-1.3.1.Final
Source0:        mod_cluster-%{commitid}.tar.gz
Source1:        %{pkg_name}.conf
Source2:        %{pkg_name}.te

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:	%{?scl_prefix}httpd-devel
%if "%{?rhel}" == "7"
#64 bit natives only on RHEL 7
ExcludeArch:   i686 i386
%endif
BuildRequires:	autoconf
BuildRequires:	zip
#For SELinux
%if "%{?rhel}" == "6"
BuildRequires: selinux-policy
%else
####%%%%{_datadir}/selinux/devel/Makefile is in -devel on RHEL 5 and RHEL 7
BuildRequires: selinux-policy-devel
%endif

### same Requiries for RHEL 6 and 7
Requires(post): policycoreutils-python
Requires(postun): policycoreutils-python

Requires:   %{?scl_prefix}httpd >= 0:2.4.6

%description
JBoss mod_cluster for Apache httpd 2.4.6.

%if %with zip
%package src-zip
Summary:     Container for the source distribution of %{pkg_name}
Group:       Development

%description src-zip
Container for the source distribution of %{pkg_name}.
%endif

%prep
%setup -q -n mod_cluster-%{commitid}

%build
zip -q -r ../%{name}-%{namedversion}-src.zip native/*

%{!?apxs: %{expand: %%define apxs %{_bindir}/apxs}}

pushd native
for i in advertise mod_manager mod_proxy_cluster mod_cluster_slotmem
do
pushd $i
%{?scl:scl enable %scl - << \EOF}
set -e
sh buildconf
./configure --with-apxs="%{apxs}"
make CFLAGS="%{optflags} -fno-strict-aliasing"
%{?scl:EOF}
popd
done
popd

%install
%{!?apxs: %{expand: %%define apxs %{_bindir}/apxs}}
install -d -m 755 $RPM_BUILD_ROOT%{_datadir}/%{pkg_name}-%{version}
install -d -m 755 $RPM_BUILD_ROOT/%{aplibdir}/
cp -p native/*/*.so ${RPM_BUILD_ROOT}/%{aplibdir}/
install -d -m 755 $RPM_BUILD_ROOT/%{_localstatedir}/cache/mod_cluster

install -d -m 755 $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d/
install -p -m 644 %{SOURCE1} \
        $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d/mod_cluster.conf

%if %with zip
install -d -m 755 $RPM_BUILD_ROOT%{_javadir}/jbossas-fordev
install -p -m 644 ../%{name}-%{namedversion}-src.zip \
        $RPM_BUILD_ROOT%{_javadir}/jbossas-fordev/
%endif

# for SELinux
install -d -m 755 $RPM_BUILD_ROOT%{_datadir}/selinux/packages/%{name}
mkdir selinux
pushd selinux
cp -p %{SOURCE2} .
touch %{name}.fc %{name}.if
make -f %{_root_datadir}/selinux/devel/Makefile
install -p -m 644 -D %{pkg_name}.pp $RPM_BUILD_ROOT%{_datadir}/selinux/packages/%{name}/%{name}.pp
popd

%clean
rm -Rf $RPM_BUILD_ROOT

%post
if [ $1 -eq 1 ] ; then
    /sbin/restorecon -Fr %{aplibdir} 2>/dev/null || :
    %{_root_sbindir}/semanage port -a -t http_port_t -p udp 23364 >/dev/null 2>&1 || :
    %{_root_sbindir}/semanage port -a -t http_port_t -p tcp 6666 >/dev/null 2>&1 || :
    %{_root_sbindir}/semanage fcontext -a -t httpd_cache_t '/var/cache/mod_cluster(/.*)?' >/dev/null 2>&1 || :
    /sbin/restorecon -R /var/cache/mod_cluster >/dev/null 2>&1 || :
    %{_root_sbindir}/semodule -i %{_datadir}/selinux/packages/%{name}/%{name}.pp 2>/dev/null || : 
    restorecon -R %{_scl_root} >/dev/null 2>&1 || :
fi 

%preun
if [ $1 -eq 0 ] ; then
  %{_root_sbindir}/semanage port -d -t http_port_t -p udp 23364 2>&1 || :
  %{_root_sbindir}/semanage port -d -t http_port_t -p tcp 6666 2>&1 || :
  %{_root_sbindir}/semodule -r mod_cluster 2>&1 || :
fi 

%files
%{!?apxs: %{expand: %%define apxs %{_bindir}/apxs}}
%defattr(0644,root,root,0755)
%doc JBossORG-EULA.txt
%doc lgpl.txt
%doc release.txt
%dir %{_localstatedir}/cache/mod_cluster
%attr(0755,root,root) %{aplibdir}/*
%config(noreplace) %{_sysconfdir}/httpd/conf.d/mod_cluster.conf
# for SELinux
%dir %{_datadir}/selinux/packages/%{name}
%{_datadir}/selinux/packages/%{name}/%{name}.pp

%if %with zip
%files src-zip
%defattr(-,root,root,-)
%{_javadir}/jbossas-fordev/*
%endif

%changelog
* Tue Feb 23 2016 Jan Kaluza <jkaluza@redhat.com> - 1.3.1-11
- update to work with rhscl

* Tue Feb 16 2016 Fernando Nasser <fnasser@redhat.com> - 1.3.1-10
- Build from source-repos

* Fri Feb 12 2016 Fernando Nasser <fnasser@redhat.com> - 1.3.1-9
- JCSP-24 postun scriptlet fails when unistalling mod_cluster-native

* Tue Dec 22 2015 Fernando Nasser <fnasser@redhat.com> - 0:1.3.1-7
- Build in the jbcs-httpd24 collection

* Tue Oct 20 2015 Permaine Cheung <pcheung@redhat.com> - 0:1.3.1-6.Final-redhat-2
- Rebuild

* Fri Apr 10 2015 Permaine Cheung <pcheung@redhat.com> - 0:1.3.1-5.Final-redhat-2
- 1.3.1.Final-redhat-2
- Remove patch for CVE-2015-0298 as it has been incorporated in the new tag

* Wed Mar 18 2015 Dustin Kut Moy Cheung <dcheung@redhat.com> - 0:1.3.1-4.Beta2-redhat-1
- add patch for CVE-2015-0298

* Mon Jan 26 2015 Permaine Cheung <pcheung@redhat.com> - 0:1.3.1-3.Beta1-redhat-1
- 1.3.1.Beta2-redhat-1

* Thu Dec 18 2014 Weinan Li <weli@redhat.com> - 0:1.3.1-2.Beta1
- Fix conf file

* Tue Nov 18 2014 Permaine Cheung <pcheung@redhat.com> - 0:1.3.1-1.Beta1
- 1.3.1.Beta1
- JWS 3.0 build
