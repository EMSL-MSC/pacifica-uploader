var csrftoken = $.cookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setup_upload_tree() {

}

//**********************************************************************
var timeoutID;

function setLogoutTimer() {
    // 10 minutes hardcoded for now
    timeoutID = window.setTimeout(logOutAndBack, 600000);
}

function logOutAndBack() {
    //alert("Logging you out");
    var jqobject = $.ajax("/logout")
    .done(function (data) {
            var logoutPage = data;
            window.open("/login", '_blank');
            window.location.href = '/';
    })
    .fail(function (obj, textStatus, error) {
        $('#currState').html('Unknown');
    })
}

function logOut() {
    //alert("Logging you out");
    var jqobject = $.ajax("/logout")
    .fail(function (obj, textStatus, error) {
        $('#currState').html('Unknown');
    })
}

function clearLogoutTimer() {
    window.clearTimeout(timeoutID);
}

function resetTimeout() {
    clearLogoutTimer();
    setLogoutTimer();
}

window.onload = function () {
    resetTimeout();
};

window.onbeforeunload = function (event) {
    logOut();
};

    //**********************************************************************

    function FilterSingleBranch(clickedNode, parentNodes) {

        resetTimeout();

        // handles the edge of a single tree branch selected where each subfolder 
        // contains one folder only
        // we handle intent by checking to see if the user actually selected a folder or
        // whether fancytree filled in the blanks.
        if (!clickedNode.selected) return parentNodes;

        // edge case is that there is only one parent node and it only has one child,
        // that that one child node is selected and that the fancy tree has "filled in the blanks"
        // and selected up the stream

        if (parentNodes.length != 1) return parentNodes;

        myparent = parentNodes[0];

        // user selected it, go with it.
        if (myparent.key == clickedNode.key) return parentNodes;

        var mychildren = myparent.getChildren();

        if (mychildren.length != 1) return parentNodes;

        myparent.selected = false;
        myparent.setTitle(parent.title);

        return FilterSingleBranch(clickedNode, mychildren);
    }

    var respondToSelect = true;

    function loadUploadTree(selected) {

        resetTimeout();

        var upload = $("#uploadFiles").fancytree("getTree");
        var root = $("#uploadFiles").fancytree("getRootNode");

        while (root.hasChildren()) {
            child = root.getFirstChild();
            child.remove();
        }

        //instNode.addChildren(selected);
        var fileList = [];

        selected.forEach(function (node) {
            fileList.push(node.key);
        });

        var pkt = JSON.stringify(fileList);

        //if (fileList.length > 0) {
        if (true) {
            var posted = { packet: pkt };
            $.post("/getBundle/", posted,
                function (data) {
                    //alert('success');
                    root.addChildren(data);

                    // update bundle size
                    var message = data[0]["data"];
                    $("#message").text(message);

                    var enabled = data[0]["enabled"];
                    document.getElementById("upload_btn").disabled = !enabled;
                })
                .fail(function (xhr, textStatus, errorThrown ) {
                    errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
                    window.open(errtext, '_self');
                });
        }

        root.setExpanded(true);
    }

    $(function () {
        $.ajaxSetup({
            cache: false,
            beforeSend: function(xhr, settings) {
                function getCookie(name) {
                    var cookieValue = null;
                    if (document.cookie && document.cookie != '') {
                        var cookies = document.cookie.split(';');
                        for (var i = 0; i < cookies.length; i++) {
                            var cookie = jQuery.trim(cookies[i]);
                            // Does this cookie string begin with the name we want?
                            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                // break;
                            }
                        }
                    }
                    return cookieValue;
                }
                if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                    // Only send the token to relative URLs i.e. locally.
                    xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
                }
            } 
        });

        $('select').select2({width:'resolve'});
        $('#instrument').prop('disabled', true);

        function loadError(e, data) {
            var error = data.error;
            if (error.status && error.statusText) {
                data.message = "Ajax error: " + data.message;
                data.details = "Ajax error: " + error.statusText + ", status code = " + error.status;
            } else {
                data.message = "Custom error: " + data.message;
                data.details = "An error occurred during loading: " + error;
            }
        }

        // Create the tree inside the <div id="tree"> element.
        $("#tree").fancytree({
            //      extensions: ["select"],
            checkbox: true,
            selectMode: 3,
            loadError: loadError,
            lazyLoad: function (event, data) {
                var node = data.node;
                // Load child nodes via ajax GET /getTreeData?mode=children&parent=1234
                data.result = {
                    url: "/getChildren",
                    data: { mode: "children", parent: node.key },
                    cache: false
                };
            },

            select: function (event, data) {

                if (!respondToSelect)
                    return;

                resetTimeout();

                node = data.node;
                var tree = $("#tree").fancytree("getTree");
                var selected = tree.getSelectedNodes(stopOnParents = true);

                // fix selections upstream
                for (var i = 0; i < selected.length; i++) {
                    selected[i].fixSelection3AfterClick();
                }

                // refresh selections
                selected = tree.getSelectedNodes(stopOnParents = true);

                // filter single branch scenario
                var filtered = FilterSingleBranch(node, selected);

                loadUploadTree(filtered);
            },
            click: function (event, data) {

                resetTimeout();

                node = data.node;
                var tree = $("#tree").fancytree("getTree");
                var clicked_item_type = $.ui.fancytree.getEventTargetType(event.originalEvent);
                if (clicked_item_type != 'checkbox' && clicked_item_type != 'expander') {
                    node.toggleExpanded();
                }
            },
            loadChildren: function (event, data) {
                // Apply parent's state to new child nodes:
                data.node.fixSelection3AfterClick();
            }
        });

        $("#uploadFiles").fancytree({
            //      extensions: ["select"],
            checkbox: false,
            selectMode: 1
        });

        $.fn.serializeFormJSON = function () {
            var o = {};
            var a = this.serializeArray();
            $.each(a, function () {
                this.value = this.value.trim();
                if (o[this.name] !== undefined) {
                    if (!o[this.name].push) {
                        o[this.name] = [o[this.name]];
                    }
                    o[this.name].push(this.value || '');
                } else {
                    o[this.name] = this.value || '';
                }
            }
            );
            return o;
        };

        $("form").submit(function (event) {

            resetTimeout();

            event.preventDefault();

            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes();
            var fileList = [];

            selected.forEach(function (node) {
                fileList.push(node.key);
            });

            var frm = $("form").serializeFormJSON();

            var pkt = { form: frm, files: fileList };

            // populate session data before showing the status page
            $.post("/postData/", { form: JSON.stringify(frm) },
                function (data) {
                    var page = "/showStatus";

                    var $dialog = $('<div></div>')
                                   .html('<iframe style="border: 0px; " src="' + page + '" width="100%" height="100%"></iframe>')
                                   .dialog({
                                       autoOpen: false,
                                       modal: true,
                                       height: 625,
                                       width: 500,
                                       title: "Upload Status"
                                   });
                    $dialog.dialog('open');
                });

            

            $.post("/upload/", { packet: JSON.stringify(pkt) },
                function (data) {
                    //alert('success');
                    //window.location.href = "/showStatus";
                    // clear the selected files and get an empty bundle

                    respondToSelect = false;

                    selected.forEach(function (node) {
                        node.setSelected(false);
                    });

                    respondToSelect = true;

                    
                    selected = tree.getSelectedNodes(stopOnParents = true);
                    

                    loadUploadTree(selected);

                });
        });

        $('#proposal').change(function () {

            resetTimeout();

            // get selected proposal
            var p = $("#proposal").val();
            prop = { proposal: p };

            var posting = $.post("/propUser/", prop,
            function (data) {
                $("#proposal_user").empty();
                $("#proposal_user").val('')
                $('#proposal_user').select2('data', null);
                $("#proposal_user").select2({
                    allowClear: true,
                    data: data
                });
            })
            .fail(function (xhr, textStatus, errorThrown) {
                errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
                window.open(errtext, '_self');
            });

            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes(stopOnParents = true);

            loadUploadTree(selected);

        });


    });

