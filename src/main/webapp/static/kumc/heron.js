function doAcceptAgreement()
{
	var frm = document.forms[0];
	var msg="";
	
	if(isEmpty(frm.txtName)) msg = "Signature required!\n";
	if(isEmpty(frm.txtSignDate)) 
		msg += "Signature Date required!\n";
	else
	{
		if(!isValidDate(frm.txtSignDate.value))
		{
			msg += "Date format wrong.";
		}
	}
	if(msg!="")
	{
		alert(msg);
		return false;
	}
	else
	{
		//frm.accepted.value='T';
		//frm.agreementbtn.value='Accept';
		//frm.submit();
	}
}

function isValidDate(sText) {
    var reDate = /(?:0[1-9]|1[0-2])\/(?:0[1-9]|[12][0-9]|3[01])\/(?:19|20\d{2})/;
    return reDate.test(sText);
}

function isEmpty(field)
{
	with (field)
	{
		if (value==null||value==""||value.trim()=="")
			return true;
		else return false;
	}
}

String.prototype.trim = function () {
    return this.replace(/^\s*/, "").replace(/\s*$/, "");
}

