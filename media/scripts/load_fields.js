
var bundled = false;
var testCount = 0

    function test_upload() {
        // entry point of async loop
        document.getElementById("testmode").value = "test " + testCount.toString();
        testCount++;
        
        // initialize flags
        bundled = false;
        var tree = $("#tree").fancytree("getTree");
        var root = $("#tree").fancytree("getRootNode");
        child = root.getFirstChild();

        child.setExpanded();
    }

    function test_loadhandler(node) {
        // assumption is there will be a 
        // "test" directory under the top directory

        // bail if we are not in testmode
        if (!isTestMode()) return;

        if (node.title == "root") return;

        var mychildren = node.getChildren();

        if (mychildren.length < 1) alert("root dir empty");

        // select "test"
        mychildren.forEach(function (child) {
            if (child.title == "test") {
                child.setSelected();
            }
        });
    }
    
    function test_bundlehandler() {
        // upload the bundle

        // bail if we are not in testmode
        if (!isTestMode()) return;

        //only handle this event once
        if (bundled) return;
        bundled = true;

        setTimeout(function () {
            $("#upload_btn").click();
        }, 1);
    }

    function test_reload() {
        // reload form, start new test

        // bail if we are not in testmode
        if (!isTestMode()) return;

        location.reload();
    }

    function isTestMode() {
        if (document.getElementById("testmode") != null)
            return true;
        else
            return false;
    }

    function initializeFields() {

        // populate session data before showing the status page
        var t = new Date()
        $.post("/initializeFields/", "{}",
            function (data) {
                updateFields(data);
                console.log("initial fields loaded");
                if (isTestMode())
                    test_upload();
            })
        .fail(function (xhr, textStatus, errorThrown) {
            //errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
            //window.open(errtext, '_blank');
            alert(xhr.responseText);
        });
    }

    function updateFields(list)
    {
        for (var i = 0; i < list.length; i++) {
            var item = list[i];
            var id = item.meta_id;
            var data = item.selection_list;

            updateField(id, data);
        }
    }

    function updateField(fieldID, data) {

        var select = "#" + fieldID;
        $(select).empty();
        $(select).val('')

        var s2 = $(select).data('select2');
        if (s2) {
            $(select).select2('data', null);
            $(select).select2({
                allowClear: true,
                data: data
            });
        }
        else {
            $(select).text(data[0].text)
        }
    }
