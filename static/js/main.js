// static/js/main.js

import * as DragAndDrop from "./core/dragAndDrop.js";
import * as IpManagement from "./core/ipManagement.js";
import * as PortManagement from "./core/portManagement.js";
import * as Modals from "./ui/modals.js";
import enhancedTooltip from "./ui/tooltip.js";

function init() {
    Modals.init();  // Initialize modals first
    enhancedTooltip.init(); // Initialize enhanced tooltip system
    DragAndDrop.init();
    IpManagement.init();
    PortManagement.init();

    console.log("Document ready");
}

document.addEventListener('DOMContentLoaded', init);
