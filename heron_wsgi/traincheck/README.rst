HERON Human Subjects Training Lookup
====================================

The HERON login system uses an outboard HTTP service to check for
human subjects training.


KUMC Local Approach
-------------------

`pom.xml` and `src/` are the JDBC approach developed in August 2011 to
access records kept in a MS SQL database at KUMC.


CITI Web Service
----------------

Records are now kept by Collaborative Institutional Training
Initiative (`CITI`__).

We're investigating the `​CITI SOAP and REST Services In BETA`__.
context: ticket:2760#comment:56.

__ https://www.citiprogram.org/
__ https://webservices.citiprogram.org/DOC/CITISOAP_Documentation.aspx


Challenges
++++++++++

Notes on shopping for a python SOAP client are in requirements.txt

We seem to be able to get their WSDL and call `HelloWorld`::

  (citi)~/projects/chalk-checker$ python traincheck.py me
  INFO:pysimplesoap.helpers:GET https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL using urllib2 2.6
  INFO:__main__:client: <pysimplesoap.client.SoapClient object at 0x1f61450>
  INFO:pysimplesoap.client:POST https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx
  INFO:__main__:CITISOAPService.HelloWorld(): {'HelloWorldResult': 'Hello World'}

But it's not clear whether `HelloWorldbyUser` is working::

  INFO:pysimplesoap.client:POST https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx
  INFO:__main__:byUser: {'HelloWorldbyUserResult': 'Authenticated as KUMC_Citi. You have No level access. You are linked to No Institution associated with this account. Institution.Your status is InValid'}

And when we try `GetCompletionReports`, we get an exception parsing the result::

  INFO:pysimplesoap.client:POST https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx
  Traceback (most recent call last):
    ...
    File "traincheck.py", line 35, in main
      reports = client.GetCompletionReports(usr=usr, pwd=pwd)
    File ".../pysimplesoap/simplexml.py", line 475, in unmarshall
      raise TypeError("Tag: %s invalid (type not found)" % (name,))
  TypeError: Tag: schema invalid (type not found)

Java Tools Look Promising
+++++++++++++++++++++++++

see Makefile for somewhat cleaned up version

Generate JAX-WS artifacts from the WSDL
http://stackoverflow.com/questions/4172118/web-service-client-given-wsdl


dconnolly@bid-bse02:~/projects/chalk-checker$ wsimport -d generated -extension -keep -p com.gatewayedi.ws -XadditionalHeaders 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL'
parsing WSDL...


[WARNING] src-resolve.4.2: Error resolving component 's:schema'. It was detected that 's:schema' is in namespace 'http://www.w3.org/2001/XMLSchema', but components from this namespace are not referenceable from schema document 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1'. If this is the incorrect namespace, perhaps the prefix of 's:schema' needs to be changed. If this is the correct namespace, then an appropriate 'import' tag should be added to 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1'.
  line 44 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1

[WARNING] src-resolve: Cannot resolve the name 's:schema' to a(n) 'element declaration' component.
  line 44 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1

[ERROR] undefined element declaration 's:schema'
  line 44 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL

[ERROR] undefined element declaration 's:schema'
  line 66 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL

[ERROR] undefined element declaration 's:schema'
  line 164 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL

[ERROR] undefined element declaration 's:schema'
  line 188 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL


wsimport -b http://www.w3.org/2001/XMLSchema.xsd -b customization.xjb

http://stackoverflow.com/questions/18898261/undefined-element-declaration-xsschema

dconnolly@bid-bse02:~/projects/chalk-checker$ wsimport -b http://www.w3.org/2001/XMLSchema.xsd -b customization.xjb -d generated -extension -keep -p com.gatewayedi.ws -XadditionalHeaders 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL'
parsing WSDL...


[WARNING] src-resolve.4.2: Error resolving component 's:schema'. It was detected that 's:schema' is in namespace 'http://www.w3.org/2001/XMLSchema', but components from this namespace are not referenceable from schema document 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1'. If this is the incorrect namespace, perhaps the prefix of 's:schema' needs to be changed. If this is the correct namespace, then an appropriate 'import' tag should be added to 'https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1'.
  line 44 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1

[WARNING] src-resolve: Cannot resolve the name 's:schema' to a(n) 'element declaration' component.
  line 44 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL#types?schema1

[WARNING] SOAP port "CITISOAPServiceSoap12": uses a non-standard SOAP 1.2 binding.
  line 442 of https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL


Generating code...


Compiling code...

Invoking Works
++++++++++++++

~/projects/chalk-checker$ javac simpleclient/Client.java generated/org/citiprogram/webservices/*.java
~/projects/chalk-checker$ java -cp generated:. simpleclient.Client
what did we win, bob?org.citiprogram.webservices.CITISOAPService@481e5c05
Retrieving the port from the following service: org.citiprogram.webservices.CITISOAPService@481e5c05
Invoking the helloWorld operation on the port.
Hello World
