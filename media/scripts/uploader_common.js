﻿var csrftoken = $.cookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setup_upload_tree() {

}

//**********************************************************************
// timer for auto logout
var timeoutID;


function logOutAndBack() {
    //alert("Logging you out");
    var jqobject = $.ajax("/logout")
    .done(function (data) {
        var logoutPage = data;
            // uh, this opens two login windows
            //window.open("/login", '_blank');
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

function setLogoutTimer() {
    // 10 minutes hardcoded for now
    timeoutID = window.setTimeout(logOutAndBack, 600000);
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
    //logOut();
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

        // kludge to update the selection state without triggering a selection event
        myparent.selected = false;
        myparent.setTitle(myparent.title);

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
        //$('#instrument').prop('disabled', true);

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

                var anchor, idx, inc,
                    tree = data.tree,
                    node = data.node;

                if (event.shiftKey) {

                    respondToSelect = false;

                    if (!anchor) {
                        // search up, select the highest selected node
                        idx = node.getIndex() - 1;
                        while (idx >= 0) {
                            if (node.parent.children[idx].isSelected() && !node.parent.children[idx].isFolder()) {
                                anchor = node.parent.children[idx];
                            }
                            idx--;
                        } 
                    }

                    if (!anchor) {
                        // search down, select the lowest selected node
                        idx = node.getIndex() + 1;
                        while (idx < node.parent.children.length) {
                            if (node.parent.children[idx].isSelected() && !node.parent.children[idx].isFolder()) {
                                anchor = node.parent.children[idx];
                            }
                            idx++;
                        }
                    }


                    // Select contigous region (only inside a common parent)
                    node.parent.visit(function (n) {
                        n.setSelected(false);
                    });
                    //node.setSelected();
                    
                    if (anchor && anchor.parent === node.parent) {
                        // select range up to active node (only if within common parent)
                        idx = anchor.getIndex();
                        inc = (idx <= node.getIndex()) ? +1 : -1;
                        do {
                            anchor.setSelected();
                            idx += inc;
                            anchor = node.parent.children[idx];
                        } while (anchor && anchor !== node);
                    }

                    respondToSelect = true;

                    var clicked_item_type = $.ui.fancytree.getEventTargetType(event.originalEvent);
                    if (clicked_item_type != 'checkbox' && clicked_item_type != 'expander') {
                        node.toggleExpanded();
                    }
                } 
            },
            loadChildren: function (event, data) {
                // Apply parent's state to new child nodes:
                data.node.fixSelection3AfterClick();

                var node = data.node;

                SortByName(node);
            }
        });

        function SortByTime(node) {
            var cmp = function (a, b) {
                var x = (a.isFolder() ? "1" : "0") + a.data.time,
                    y = (b.isFolder() ? "1" : "0") + b.data.time;

                // sort with newest first
                return x === y ? 0 : x > y ? -1 : 1;
            };
            node.data["sorting"] = "sortTime";
            node.sortChildren(cmp, false);
        }

        function SortByName(node) {
            var cmp = function (a, b) {
                var x = (a.isFolder() ? "0" : "1") + a.title,
                    y = (b.isFolder() ? "0" : "1") + b.title;

                // sort with newest first
                return x === y ? 0 : x > y ? 1 : -1;
            };
            node.data["sorting"] = "sortName";
            node.sortChildren(cmp, false);
        }

        function SetRoot(setmode, root) {
            $.post("/setRoot/", {mode:setmode, parent: root },
            function (data) {
                // reload the page
                document.location.reload(true);
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                alert(jqXHR.responseText);
            });
        }



        $("#tree").contextmenu({
            delegate: "span.fancytree-node",
            //      menu: "#options",
            menu: [
                { title: "Set as Base Directory", cmd: "reroute" },
                { title: "Restore Base Directory", cmd: "root" },
                { title: "Sort by Timestamp", cmd: "sortTime" },
                { title: "Sort by Name", cmd: "sortName" }
            ],
            show: { effect: "fadeIn", duration: 100 },
            hide: { effect: "fadeOut", duration: 100 },
            beforeOpen: function (event, ui) {
                var node = $.ui.fancytree.getNode(ui.target);
                var sort_type = "sortName";
                if ("sorting" in node.data){
                    sort_type = node.data.sorting;
                }
                var menu_replacement = [];

                if (node.isFolder()) {
                    menu_replacement.push({ title: "Set as Base Directory", cmd: "reroute" });
                    menu_replacement.push({ title: "Restore Base Directory", cmd: "root" });
                    if (sort_type == 'sortName') {
                        menu_replacement.push({ title: "Sort by Time", cmd: "sortTime" });
                    } else {
                        menu_replacement.push({ title: "Sort by Name", cmd: "sortName" });
                    }
                    $("#tree").contextmenu("replaceMenu", menu_replacement);
                }
                else {
                    $("#tree").contextmenu("replaceMenu", []);
                }

                node.setActive();
            },
            select: function (event, ui) {
                var node = $.ui.fancytree.getNode(ui.target);

                resetTimeout();

                switch (ui.cmd)
                {
                    case "reroute":
                        SetRoot("set", node.key);
                        break;
                    case "root":
                        SetRoot("restore", "");
                        break;
                    case "sortTime":
                        SortByTime(node);
                        break;
                    case "sortName":
                        SortByName(node);
                        break;
                }
                
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

            // stop the logout timer
            clearLogoutTimer();

            event.preventDefault();

            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes();
            var fileList = [];

            selected.forEach(function (node) {
                fileList.push(node.key);
            });

            if (jQuery.isEmptyObject(fileList)) {
                alert("upload list is empty");
                return;
            }

            var frm = $("form").serializeFormJSON();

            // populate session data before showing the status page
            $.post("/postData/", { form: JSON.stringify(frm) },
                function (data) {
                    var page = "/showStatus";

                    $.get(page, function (status_data) {
                        $('#status_info_container').html(status_data);
                    });

                    $('#status_info_container').dialog({
                        autoOpen: true,
                        modal: true,
                        width: 500,
                        title: "Upload Status",
                        buttons: {
                            "Cancel Upload": function () {
                                $.post("/incStatus/", "Cancel Upload",
                                function (data) {
                                    $('#status_info_container').dialog('close');
                                });
                            }
                        },
                        close: function (event, ui) {
                            // stop the status update timer
                            window.clearTimeout(statusTimeoutHandler);

                            respondToSelect = false;

                            selected.forEach(function (node) {
                                node.setSelected(false);
                            });

                            respondToSelect = true;


                            selected = tree.getSelectedNodes(stopOnParents = true);


                            loadUploadTree(selected);

                            // restart the logout timer
                            resetTimeout();
                        }
                    });

                    $.post("/upload/", { files: JSON.stringify(fileList) },
                        function (data) {})
                        .fail(function (jqXHR, textStatus, errorThrown) {
                            alert(jqXHR.responseText);
                        });
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

            // commenting this out until we figure out wtf we are doing for analytical 
            // selection priorities (dfh 8.26.16)
            //var posting = $.post("/propInstruments/", prop,
            //function (data) {
            //    $("#instrument").empty();
            //    $("#instrument").val('')
            //    $('#instrument').select2('data', null);
            //    $("#instrument").select2({
            //        allowClear: true,
            //        data: data
            //    });
            //})
            //.fail(function (xhr, textStatus, errorThrown) {
            //    errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
            //    window.open(errtext, '_self');
            //});

            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes(stopOnParents = true);

            loadUploadTree(selected);

        });

        $('#instrument').change(function () {

            resetTimeout();

            i = $("#instrument").val();
            instStr = { instrument: i };


            var posting = $.post("/setInstrument/", instStr,
            function (data) {
            })
            .fail(function (xhr, textStatus, errorThrown) {
                errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
                window.open(errtext, '_self');
            });
        });

    });

