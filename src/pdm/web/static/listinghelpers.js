// All javascript functions related to listing files and directories


// displays page content once page is ready
function makepage() {
    // this is currently a dummy
} // makepage


function get_query_result(){
    var sitename = encodeURIComponent($("#Endpoints").val());
    var sitepath = encodeURIComponent($("#pathatsite").val());
    var fullpath = "/web/js/list?siteid="+sitename+"&sitepath="+sitepath;
    $.ajax({url: fullpath, success: function(result) {
        $("#jobnumberfield").val(result);
    }});
} // get_query_result


// gets the status of the request and if it is DONE or FAILED displays the result
function get_query_status(){
    var j = encodeURIComponent($("#jobnumberfield").val());
    get_status(j);
} // get_query_status



//  TODO: Deal with 'FAILED' and all other states beyong 'DONE' correctly.
function get_status(jobid) {
    var fullpath = "/web/js/status?jobid="+jobid;
    $.ajax({url: fullpath, success: function(result) {
        alert(result);
        // this is a javascript object
        var jobobj = JSON.parse(result);

	// Found something ? Display if in a table
	if (jobobj.status == "DONE") {

            // make a table
            var n_of_rows = jobobj.listing.length;
            // TODO: apparently html5 doesn't do borders and needs a css instead
            var table_body = '<table id="table1"><thead><tr><th> permissions </th> <th> nlinks </th><th> userid </th> <th> groupi\ d </th> <th> size </th> <th> date </th> <th> file name </th></thead><tbody>';
            for (i =0; i < n_of_rows; i++) {
		table_body += '<tr>';
		table_body += '<td>';
		table_body += jobobj.listing[i]['permissions'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['nlinks'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['userid'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['groupid'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['size'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['datestamp'];
		table_body +='</td><td>';
		if (jobobj.listing[i]['is_directory'] == true) { table_body += '<font color="blue">';}
		table_body += jobobj.listing[i]['name'];
		if (jobobj.listing[i]['is_directory'] == true) { table_body += '</font>';}
		table_body +='</td></tr>';
            }
            table_body+='</tbody></table>';
            $('#tableDiv').html(table_body);
        } // DONE
	$("#reqstatus").html(jobobj.status);
    }});
} // get_status
