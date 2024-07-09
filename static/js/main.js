// static/js/main.js

import * as DragAndDrop from "./core/dragAndDrop.js";
import * as IpManagement from "./core/ipManagement.js";
import * as PortManagement from "./core/portManagement.js";
import * as Modals from "./ui/modals.js";

function init() {
    Modals.init();  // Initialize modals first
    DragAndDrop.init();
    IpManagement.init();
    PortManagement.init();
}

document.addEventListener('DOMContentLoaded', init);