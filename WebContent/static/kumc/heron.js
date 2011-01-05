function doAcceptAgreement()
{
	var frm = document.forms[0];
	var msg="";
	
	if(isEmpty(frm.txtName)) msg = "Signature required!\n";
	if(isEmpty(frm.txtSignDate)) msg += "Signature Date required!\n";
	if(msg!="")
	{
		alert(msg);
		return false;
	}
	else
	{
		frm.accepted.value='T';
		frm.submit();
	}
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

